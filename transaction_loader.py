# transcation_loader.py : this file is used to load the transcation data from csv to list of dicts

import pandas as pd

def load_transactions(sample=10000):
    df = pd.read_csv("data/HISmallTrans.csv")
    df.columns = [col.lower().replace(" ", "_") for col in df.columns]

    laundering = df[df['is_laundering'] == 1].head(100)
    normal = df[df['is_laundering'] == 0].head(sample - 100)
    
    mixed = pd.concat([laundering, normal]).sample(frac=1).reset_index(drop=True)

    return mixed.to_dict(orient='records')
        
