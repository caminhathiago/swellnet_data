import pickle
from datetime import datetime, timedelta, timezone


def generate_checkpoint_contents(station, key, last_modified):
    return {
        station:{
            "key":key,
            "last_modified":last_modified
        }
    }

def save_checkpoint(station, key, last_modified, checkpoint_file):
    
    contents = load_checkpoint(checkpoint_file)

    if contents is None:
        contents = {}

    if station not in contents:
        contents[station] = {}
    
    contents[station].update({
        'key':key,
        'last_modified':last_modified
    })

    with open(checkpoint_file, "wb") as f:
        pickle.dump(contents, f)


def load_checkpoint(checkpoint_file):
    try:
        with open(checkpoint_file, "rb") as f:
            return pickle.load(f)
    except:
        raise FileNotFoundError(f"{checkpoint_file} not found.")
    
def create_new_station(station, contents, checkpoint_file):

    if station not in contents:
        contents[station] = {}

    if "key" not in contents[station]:
        contents[station].update({
            'key':None,
            'last_modified':None
        })

        with open(checkpoint_file, "wb") as f:
            pickle.dump(contents, f)


    return contents
