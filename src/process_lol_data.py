import pandas as pd
import os
from riotwatcher import LolWatcher, ApiError

RIOT_API_KEY = os.environ.get("RIOT_API_KEY")

#TODO:
# - Complete testing

def process_player_data_from_matches(load_path: str, save_path: str | None = None, include_key: bool = True):

    """
    Args:
        load_path: Path to raw_match_data.
        save_path: Path to save processed_player_data.
        include_key: Will column of keys if true.
    Returns:
        Processed player data as DataFrame object.
        Name of save file (Optional).
    """
    
    # Compiling players present in match data into DataFrame format.

    match_data = pd.read_csv(load_path)
    
    try:
        combined_player_names = match_data.loc[:, ['p1_name', 'p1_puuid', 'p1_summonerId']]
    except KeyError as e:
        print('File at ' + load_path + ' has invalid format')
        raise

    combined_player_names = combined_player_names.rename(columns = {'p1_name': 'name',
                                                                    'p1_puuid': 'puuid',
                                                                    'p1_summonerId': 'summonerId'})

    for i in range(2,11):
        
        try:
            player_names = match_data.loc[:, ['p{p_num}_name'.format(p_num = i),
                                            'p{p_num}_puuid'.format(p_num = i), 
                                            'p{p_num}_summonerId'.format(p_num = i)]]
        except KeyError:
            print('File at ' + load_path + ' has invalid format')
            raise

        player_names = player_names.rename(columns = {'p{p_num}_name'.format(p_num = i): 'name',
                                                      'p{p_num}_puuid'.format(p_num = i): 'puuid',
                                                      'p{p_num}_summonerId'.format(p_num = i): 'summonerId'})

        combined_player_names = pd.concat([combined_player_names, player_names], ignore_index = True)
        combined_player_names = combined_player_names.drop_duplicates( ignore_index = True)
    
    # Adding column for unknown player.
    unknown_row = pd.DataFrame({'name': ['<U>'], 'puuid': ['0'], 'summonerId': ['0']})
    combined_player_names = pd.concat([unknown_row, combined_player_names], ignore_index = True)
    
    # Add column of keys if include_key == True.
    if include_key == True:
        combined_player_names['key'] = combined_player_names.index
        
    # Saving data.
    match_data_file_name = os.path.split(load_path)[1]
    if not (save_path is None):
        try:
            combined_player_names.to_csv(save_path + match_data_file_name.replace('raw_match_data', 'processed_player_data'), index = False)
        except Exception as e:
            print('Failed to save processed player data to .csv file.')
            raise
        else:
            return combined_player_names, match_data_file_name.replace('raw_match_data', 'processed_player_data')
    
    return combined_player_names

def process_match_data (match_load_path: str, player_load_path: str, save_path: str | None = None, noise_rate: float = 0):

    """
    Args:
        match_load_path: Path to raw_match_data.
        player_load_path: Path to processed_player_data.
        save_path: Path to save processed_match_data.
        noise_rate = Proportion of player names and key to delete from match data. 
    Returns:
        Processed match data as DataFrame object.
        Name of save file (Optional).
    """
    
    assert 0 <= noise_rate <= 1, 'Invalid noise_rate (must be in-between 0 and 1).'

    try:
        match_data = pd.read_csv(match_load_path)
        player_data = pd.read_csv(player_load_path)
        player_data = player_data.drop(columns = ['puuid', 'summonerId'])
    except FileNotFoundError as e:
        print('Invalid load paths')
        raise
    
    # Check for invalid API key.
    try:
        watcher = LolWatcher(RIOT_API_KEY) 
        latest_version = watcher.data_dragon.versions_for_region('na1')['n']['champion']
        static_champ_list = watcher.data_dragon.champions(latest_version, False, 'en_US')
    except ApiError as e:
        if e.response.status_code == 401:
            print('Invalid API key.')
            raise
        else:
            raise

    champ_dict = {int(static_champ_list['data'][champ]['key']):
              static_champ_list['data'][champ]['name'] for champ in static_champ_list['data']}
    
    for i in range(1, 11):
        
        # Remove unnecessary columns for player i.
        match_data = match_data.drop(columns = ['p{p_num}_puuid'.format(p_num = i),
                                                'p{p_num}_summonerId'.format(p_num = i)])
        
        # Add noise - randomly delete 0.1 * player names from column p{i}_name.
        row_indices = match_data.sample(frac = noise_rate).index
        match_data.loc[row_indices, ['p{p_num}_name'.format(p_num = i)]] = '<U>'
        
        # Add key column of keys for player i.
        match_data = match_data.join(player_data.set_index('name'), on = 'p{p_num}_name'.format(p_num = i))
        match_data = match_data.rename(columns = {'key': 'p{p_num}_key'.format(p_num = i )})

        # Adding column for name of champion of player i.
        match_data['p{p_num}_champName'.format(p_num = i)] = match_data['p{p_num}_champId'.format(p_num = i)].map(champ_dict)
        
    # Reordering columns.
    ordered_cols = ['match_id']
    for i in range(1, 11):
        ordered_cols.append('p{p_num}_name'.format(p_num = i))
        ordered_cols.append('p{p_num}_key'.format(p_num = i))
        ordered_cols.append('p{p_num}_champId'.format(p_num = i))
        ordered_cols.append('p{p_num}_champName'.format(p_num = i))
        ordered_cols.append('p{p_num}_win'.format(p_num = i))
    
    match_data_processed = match_data[ordered_cols]
    
    # Saving data.
    match_data_file_name = os.path.split(match_load_path)[1]
    if not (save_path is None):
        try:
            match_data_processed.to_csv(save_path + match_data_file_name.replace('raw_match_data', 'processed_match_data'), index = False)
        except Exception as e:
            print('Failed to save processed match data to .csv file.')
            raise
        else:
            return match_data_processed, match_data_file_name.replace('raw_match_data', 'processed_match_data')

    return match_data_processed