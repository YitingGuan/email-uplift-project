"""Download the exact source used by scikit-uplift's Hillstrom loader."""
from pathlib import Path
import urllib.request,hashlib
ROOT=Path(__file__).resolve().parents[1]
URL='https://hillstorm1.s3.us-east-2.amazonaws.com/hillstorm_no_indices.csv.gz'
MD5='a68a81291f53a14f4e29002629803ba3'
SHA256='bab6578f60db5d792f1c2372c502f029152a5249cf5ea84390f3b7f885d7234f'
def download():
    path=ROOT/'data/raw/hillstrom.csv.gz'
    if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()==SHA256:return path
    with urllib.request.urlopen(URL,timeout=60) as r:b=r.read()
    if hashlib.sha256(b).hexdigest()!=SHA256:raise ValueError('Source digest changed; review data before proceeding')
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b)
    return path
if __name__=='__main__':print(download())
