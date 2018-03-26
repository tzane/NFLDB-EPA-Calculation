import csv
import numpy as np
import nfldb

# Empty arrays where EPA data will be later appended to
# Data point for every yardline
EPA_observed = np.zeros(100)
EPA_play = np.zeros(100)

# This query generates a data set of all regular season games from 2017 season
db = nfldb.connect()
q = nfldb.Query(db) 
games = q.game(season_year=[2016], season_type='Regular').as_games()


# This function onverts yardline string (e.g. "OWN 15") to integer 1-99 
def yardstr_to_num(yard_text):
    
    yard_split = yard_text.split()
    pos_indicate = yard_split[0]
    
    if pos_indicate == 'OWN':
		yardline_from_str = int(yard_split[1])
		return yardline_from_str
    elif pos_indicate == 'OPP':
		yardline_from_str = 100 - int(yard_split[1])
		return yardline_from_str
    else:
        yardline_from_str = 50
        return yardline_from_str
 
# Use this function to iterate over all plays to calcualte observed EPA 
def iterate_plays(nfldb_obj, deduct_punts=False):
    for game in nfldb_obj:
        for drive in game.drives:
            if drive.result == 'Field Goal' or drive.result == 'Punt' or drive.result == 'Touchdown' or drive.result == 'Missed FG' or drive.result == 'Safety' or drive.result == 'Fumble, Safety' or drive.result == 'Interception' or drive.result == 'Fumble':
                for play in drive.plays:
                    if (play.passing_att == 1 or play.rushing_att == 1 or play.passing_sk == 1) and int(play.down) == 1:
					
						yardlinefromstr	= yardstr_to_num(str(play.yardline))
						
						if deduct_punts:
							end_field_fromstr = yardstr_to_num(str(drive.end_field))					
							
						if int(play.down) == 1:
							if drive.result == 'Field Goal':
								EPA_play[yardlinefromstr-1] += 1
								EPA_observed[yardlinefromstr-1] += 3
							if drive.result == 'Missed FG':
								EPA_play[yardlinefromstr-1] += 1
							if drive.result == 'Interception':
								EPA_play[yardlinefromstr-1] += 1
								if deduct_punts:
									EPA_observed[yardlinefromstr-1] -= temp_EPA[100-end_field_fromstr]
							if drive.result == 'Fumble':
								EPA_play[yardlinefromstr-1] += 1
								if deduct_punts:
									EPA_observed[yardlinefromstr-1] -= temp_EPA[100-end_field_fromstr]
							if drive.result == 'Punt':
								EPA_play[yardlinefromstr-1] += 1
								if deduct_punts:
									EPA_observed[yardlinefromstr-1] -= temp_EPA[100 - int(-0.0116 * end_field_fromstr * end_field_fromstr + 1.5343 * end_field_fromstr + 37.91) - 1]
							if drive.result == 'Safety' or drive.result == 'Fumble, Safety':
								EPA_play[yardlinefromstr-1] += 1
								EPA_observed[yardlinefromstr-1] -= 2
							if drive.result == 'Touchdown':
								EPA_play[yardlinefromstr-1] += 1
								EPA_observed[yardlinefromstr-1] += 7

# Call this function on the full data set to generate total points and plays observed for every yard line
# Appends data to the two np arrays				
iterate_plays(games)

# Repeat the calculation to deduct points for punts and merge both arrays into one single baseline EPA array
for i in range(4):
    for j in range(99):
	    if EPA_play[j] > 0:
		    EPA_observed[j] = float(EPA_observed[j] / EPA_play[j])
			
    temp_EPA = EPA_observed
    EPA_observed = np.zeros(100)
    EPA_play = np.zeros(100)
	
    iterate_plays(games, deduct_punts=True)

# Merge one final time 	
for j in range(99):
	    if EPA_play[j] > 0:
		    EPA_observed[j] = float(EPA_observed[j] / EPA_play[j])

# Need to exponentially smooth the curve			
cof = np.polyfit(np.linspace(1,99,num=99),EPA_observed[0:99],5)

x = np.linspace(1,99,num=99)

EPA_observed_smooth = cof[0]*x**5 + cof[1]*x**4 + cof[2]*x**3 + cof[3]*x**2 + cof[4]*x + cof[5]

# Set up an array that will later append cumulative EPA for full 2017 season for every team
team_list = np.array(['ARI','ATL','BAL','BUF','CAR','CHI','CIN','CLE','DAL','DEN','DET','GB','HOU','IND','JAX','KC','LA','MIA','MIN','NE','NO'
                 ,'NYG','NYJ','OAK','PHI','PIT','SD','SEA','SF','TB','TEN','WAS'])	

week_array = [i+1 for i in range(17)]
week = 17
EPA_team = np.zeros(32)

next_drive_start_yardline = 50

epa_result = np.empty(0)

# Here we iterate through every single drive result for every team in 2017 and calcualte EPA based on drive outcome vs. EPA baseline array
for game in games:
    for drive in game.drives:
        
        if str(game.home_team) == str(drive.pos_team):
            opp_team = str(game.away_team)
        else:
            opp_team = str(game.home_team)
		
        yardlinefromstr = yardstr_to_num(str(drive.start_field))
		
        EP_start = EPA_observed_smooth[yardlinefromstr-1]

        end_field_fromstr = yardstr_to_num(str(drive.end_field))
		
        if drive.result == 'End of Game' or drive.result == 'End of Half':
		    EP_end = EP_start
			
        if drive.result == 'Missed FG' or drive.result == 'Interception' or drive.result == 'Fumble' or drive.result == 'Downs' or drive.result == 'Blocked FG' or drive.result == 'Blocked Punt' or drive.result == 'Blocked FG, Downs' or drive.result == 'Blocked Punt, Downs':
		    EP_end = -EPA_observed_smooth[100-end_field_fromstr-1]
		
        if drive.result == 'Punt':
            EP_end = -EPA_observed_smooth[next_drive_start_yardline-1]
			
        if drive.result == 'Touchdown':
            EP_end = 7
		
        if drive.result == 'Field Goal':
		    EP_end = 3
			
        if drive.result == 'Fumble, Safety' or drive.result == 'Safety':
		    EP_end = -2 - EPA_observed_smooth[next_drive_start_yardline-1]
			
        epa_result = np.append(epa_result,(EP_end-EP_start))

        if drive.pos_team == 'JAC':
            drive.pos_team = 'JAX'
        if opp_team == 'JAC':
            opp_team = 'JAX'		

        EPA_team[np.where(team_list==drive.pos_team)[0][0]] += ( EP_end - EP_start )

        EPA_team[np.where(team_list==opp_team)[0][0]] -= ( EP_end - EP_start )    

        next_drive_start_yardline = yardlinefromstr
		
bye_week = [9,11,8,10,7,9,9,13,7,11,10,4,9,10,5,5,8,8,6,9,5,8,11,10,4,8,11,5,8,6,13,9]

Estimated_wins = np.zeros(32)

for i in range(32):
    
    if week < bye_week[i]:
        game_count = week
    else:
        game_count = week - 1
      
    EPA_team[i] = EPA_team[i] / game_count *16
    Estimated_wins[i] = 16*(1/(1+(2.7128**(-(0.0085*EPA_team[i])))))
    
    print(team_list[i],EPA_team[i])

np.savetxt('EPA_2017.csv',EPA_team,delimiter=',')