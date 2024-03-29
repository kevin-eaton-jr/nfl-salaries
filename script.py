import requests
from bs4 import BeautifulSoup
import pandas as pd
import streamlit as st

salary_url = 'https://www.spotrac.com/nfl/cap/'
webpage = requests.get(salary_url)

# this returned NaN for 'cap' columns
# salary_data = pd.read_html(webpage.text)[0]
# salary_data.head()

soup = BeautifulSoup(webpage.text)

html_table = soup.find('table')
html_data = html_table.find_all('tr')[1:]
html_cols = soup.find_all('th')
cols = [col.text for col in html_cols]

df = pd.DataFrame(columns = cols)

for row in html_data:
  html_row_data = row.find_all('td')
  row_data = [data.text.strip() for data in html_row_data]

  if row_data[0] == 'League Average':
    continue

  row_data[4] = row_data[4].strip('$').replace(',', '')
  row_data[5] = row_data[5].strip('$').replace(',', '')
  row_data[6] = row_data[6].split('$')[1].replace(',', '')
  row_data[7] = row_data[7].split('$')[1].replace(',', '')
  row_data[8] = row_data[8].split('$')[1].replace(',', '')
  row_data[9] = row_data[9].split('$')[1].replace(',', '')

  length = len(df)
  df.loc[length] = row_data

num_cols = ['Rank', 'Signed', 'Avg Age', 'Active', 'Dead', 'Top 51 Cap',
            'Cap Space(Top 51)', 'Total Cap', 'Cap Space(All)']

df['Dead'][df['Dead'] == '0 -'] = 0
df[num_cols] = df[num_cols].apply(pd.to_numeric)

html_team_urls = html_table.find_all('a')
team_url = [url.get('href') for url in html_team_urls]
df['Team URL'] = team_url

for ind in df.index:
  team_name = df.loc[ind, 'Team'].split('\n')[1]
  team_url = df.loc[ind, 'Team URL']
  team_webpage = requests.get(team_url)
  team_soup = BeautifulSoup(team_webpage.text)
  team_html_table = team_soup.find('table')

  if ind == 0:
    team_html_cols = team_soup.find_all('th')[:13]
    cols = [col.text for col in team_html_cols]
    cols[0] = cols[0][:-5]
    cols = cols + ['Team']
    team_df = pd.DataFrame(columns = cols)

  player_html_data = team_html_table.find_all('tr')[1:]

  for row in player_html_data[:-1]:
    html_row_data = row.find_all('td')
    player_row_data = [data.text.strip() for data in html_row_data]
    player_row_data[0] = player_row_data[0].split()
    player_row_data[0] = ' '.join(player_row_data[0][(len(player_row_data[0]) \
                                                      // 2):])
    player_row_data[0] = player_row_data[0].upper()

    for i in range(len(player_row_data)-2):
      player_row_data[i+2] = player_row_data[i+2].replace('$', '')
      player_row_data[i+2] = player_row_data[i+2].replace(',', '')
      player_row_data[i+2] = player_row_data[i+2].replace('0-', '0')
      player_row_data[i+2] = player_row_data[i+2].replace('(', '-')
      player_row_data[i+2] = player_row_data[i+2].replace(')', '')
      player_row_data[i+2] = player_row_data[i+2].split()[0]

    length = len(team_df)
    team_df.loc[length] = player_row_data + [team_name]

# remove duplicate columns
team_df = team_df.loc[:,~team_df.columns.duplicated()].copy()

num_cols = list(team_df.columns[2:-1])
team_df[num_cols] = team_df[num_cols].apply(pd.to_numeric)

depth_chart_url = 'https://www.ourlads.com/nfldepthcharts/depthcharts.aspx'
depth_chart_webpage = requests.get(depth_chart_url)
depth_chart_soup = BeautifulSoup(depth_chart_webpage.text)
depth_chart_table_html = depth_chart_soup.find('table')
depth_chart_html_data = depth_chart_table_html.find_all('tr')[4:]
depth_chart_columns_html = depth_chart_table_html.find_all('th')
depth_chart_cols = [col.text for col in depth_chart_columns_html]
depth_chart_df = pd.DataFrame(columns = depth_chart_cols)

for row in depth_chart_html_data:
  html_row_data = row.find_all('td')
  row_data = [data.text.strip() for data in html_row_data]
  length = len(depth_chart_df)

# check for intermediate headers rows in table
  if(len(row_data) != 12):
    continue

  if(row_data[1] in ['FUT', 'RES', 'FACC']):
    continue

# check for name already in dataframe
  if(sum([row_data[3] in name for name in depth_chart_df['Player 1']])):
    continue

  depth_chart_df.loc[length] = row_data

depth_chart_df['Player 1'] = depth_chart_df['Player 1']. \
    apply(lambda x: x.split()[:-1])

depth_chart_df['Player 1'] = depth_chart_df['Player 1']. \
    apply(lambda x: [data.replace(',', '') for data in x])

depth_chart_df['Player 1'] = depth_chart_df['Player 1']. \
    apply(lambda x: x[-1:] + x[:-1])

depth_chart_df['Player 1'] = depth_chart_df['Player 1']. \
    apply(lambda x: ' '.join(x))

depth_chart_df['Player 1'] = depth_chart_df['Player 1']. \
    apply(lambda x: x.upper())

depth_chart_df['Player 1'] = depth_chart_df['Player 1']. \
    apply(lambda x: x.replace('Ñ', 'N'))

# check for mismatched team abbreviations between two dataframes
# team_list = [(team, team in depth_chart_df['Team'].unique())
#     for team in team_df['Team'].unique()]
#
# for team in team_list:
#   if not team[1]:
#     print(team)

depth_chart_df['Team'][depth_chart_df['Team'] == 'ARZ'] = 'ARI'
depth_chart_df['Team'][depth_chart_df['Team'] == 'JAX'] = 'JAC'

merged_df = team_df.merge(depth_chart_df,
                          left_on = ['Active Players', 'Team'],
                          right_on = ['Player 1', 'Team'])[['Active Players',
                                                            'Team',
                                                            'Cap Hit',
                                                            'Base Salary',
                                                            'Pos',]]

merged_df['Pos'][merged_df['Pos'].str.contains('WR')] = 'WR'
merged_df['Pos'][merged_df['Pos'].str.contains('DT|NT', regex = True)] = 'DT'
merged_df['Pos'][merged_df['Pos'].str.contains('ILB|MLB', regex = True)] = 'ILB'
merged_df['Pos'][merged_df['Pos'].str.contains('OLB|SLB|WLB',
                                               regex = True)] = 'OLB'
merged_df['Pos'][merged_df['Pos'].str.contains('CB|NB', regex = True)] = 'CB'
merged_df['Pos'][merged_df['Pos'].str.contains('DE|RUSH', regex = True)] = 'DE'
merged_df['Pos'][merged_df['Pos'].str.contains('LG|RG', regex = True)] = 'G'

pd.options.display.float_format = '${:,.2f}'.format

average_starter_sal = merged_df[['Pos', 'Cap Hit','Base Salary']]. \
    groupby('Pos').mean().sort_values(by = 'Cap Hit', ascending = False)

average_starter_sal['Pos'] = average_starter_sal.index

off_pos = ['C', 'FB', 'G', 'LT', 'QB', 'RB', 'RT', 'TE', 'WR']
def_pos = ['CB', 'DE', 'DT', 'FS', 'ILB', 'OLB', 'SS']
st_pos = ['PK', 'LS', 'PT', 'PR', 'KR']

average_starter_sal['Unit'] = 'DEF'

average_starter_sal['Unit'][[(pos in off_pos)
    for pos in average_starter_sal['Pos']]] = 'OFF'

average_starter_sal['Unit'][[(pos in st_pos)
    for pos in average_starter_sal['Pos']]] = 'ST'

weighted_sal = merged_df.groupby('Pos').agg(
  {'Pos': ['count'], 'Cap Hit': 'mean'}).sort_values(('Cap Hit', 'mean'),
                                                     ascending = False)

weighted_sal['wt'] = weighted_sal.loc[:,'Pos']/32
weighted_sal['Weighted Cap Hit'] = (weighted_sal.loc[:, 'Cap Hit']['mean']
                                    * weighted_sal['wt'])
weighted_sal['Unit'] = average_starter_sal['Unit']

weighted_sal.columns = weighted_sal.columns.droplevel(1)
weighted_sal.rename(columns = {'wt': 'Avg Num Players Per Team'},
                    inplace = True)

st.title('Average NFL Starter Compensation by Position')
st.bar_chart(average_starter_sal, x = 'Pos', y = 'Cap Hit',
             color = 'Unit')

col1, col2 = st.columns([0.45, 0.55])

col1.subheader('Average Compensation by Position', divider = 'gray')
col1.dataframe(average_starter_sal[['Cap Hit', 'Base Salary',
                                    'Unit']].round(0), height = 775)

col2.subheader('Average Weighted Compensation by Position',
               divider = 'gray')
col2.dataframe(weighted_sal[['Weighted Cap Hit',
                             'Avg Num Players Per Team',
                             'Unit']].round(1).sort_values('Weighted Cap Hit',
                                                           ascending = False), use_container_width = True, height = 775)

st.subheader('Average Total Cap Hit by Unit', divider = 'gray')
st.dataframe(weighted_sal[['Weighted Cap Hit',
                           'Unit']].groupby('Unit').sum().round(0).sort_values('Weighted Cap Hit',
                                                                               ascending = False))
