import requests,os,json
from dotenv import load_dotenv

load_dotenv()

key = os.getenv("KEY")
id_list = []
jumps = 0

def id_to_name(id):
    url = f'http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={key}&steamids={id}'
    r = requests.session()
    data = json.loads(r.get(url).text)
    return data['response']['players'][0]['personaname']

def vanity_to_id(link):
    url = f"http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={key}&vanityurl={link[30:]}"
    r = requests.session()
    data = json.loads(r.get(url).text)
    return int(data['response']['steamid'])

def get_friends_ids(id):
    url = f'http://api.steampowered.com/ISteamUser/GetFriendList/v0001/?key={key}&steamid={id}&relationship=friend'
    r = requests.session()
    list = []
    #try:
    data = json.loads(r.get(url).text)
    #except Exception:
        #data = {}
    try:
        for i in data['friendslist']['friends']:
            list.append(int(i['steamid']))
    except KeyError:
        list = []
    return list




if __name__=='__main__':
    #main()
    multitask([76561198217588376])


