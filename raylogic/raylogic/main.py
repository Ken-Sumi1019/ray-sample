import ray
import time
import numpy as np
from typing import Dict

# ray.init()

import paramiko

##########################################
# ftpサーバーからファイルをダウンロードする
##########################################
def create_sftp_connection():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy)
    client.connect(
        "sftp",
        "22",
        "testuser",
        "testpass",
    )

    return client.open_sftp()

file_names = create_sftp_connection().listdir("./data")


import asyncio
# 並列数が多すぎるとftpサーバーがパンクするので10並列に抑える
@ray.remote(max_concurrency=10)
class SSHResult:
    async def copy_sftp_to_result_with_ray(self, file_name):
        create_sftp_connection().get(f"./data/{file_name}", "/app/sftp/result/" + file_name)

future_ids = []
sshresult = SSHResult.remote()
ray.get([sshresult.copy_sftp_to_result_with_ray.remote(file_name) for file_name in file_names])


##########################################
## Ray Dataを使ってデータを操作する
##########################################
import mysql.connector
def create_mysql_connection():
    return mysql.connector.connect(
        host="db",
        user="root",
        password="password",
        database="employees",
        connection_timeout=30,
    )

def caesar(plain):
    key = 65
    enc = ""

    for char in plain:
        ascii_code = ord(char)
        num = ascii_code - 97
        num = (num + key) % 26
        ascii_code = num + 97
        enc += chr(ascii_code)
    return enc

def encript(batch: Dict[str, np.ndarray]):
    result_title = [caesar(v) for v in batch["title"]]
    batch["title"] = result_title
    return batch

# データベースの値をRay Dataに読み込み
ds = ray.data.read_sql("select * from titles", create_mysql_connection)
# データをディレクトリにCSV形式で出力
ds.write_csv("raw")
# 出力したデータからRay Dataに読み込み
ds_from_csv = ray.data.read_csv("raw")
# 自作した関数(encript)を各行に適用
converted_ds = ds_from_csv.map_batches(encript)

converted_ds.write_csv("encripted")


##########################################
## 自作の関数を並行実行する
##########################################
def tarai_non_ray(x, y, z):
    if x <= y:
        return y 
    return tarai_non_ray(
        tarai_non_ray(x - 1, y, z),
        tarai_non_ray(y - 1, z, x),
        tarai_non_ray(z - 1, x, y)
    )

@ray.remote
def tarai(x, y, z):
    if x <= y:
        return y 
    return tarai_non_ray(
        tarai_non_ray(x - 1, y, z),
        tarai_non_ray(y - 1, z, x),
        tarai_non_ray(z - 1, x, y)
    )

time_sta = time.time() # 時間計測用
# プレーンなpythonで直列に実行する
for i in range(10):
    tarai_non_ray(13, 7, 0)
time_end = time.time()
tim = time_end- time_sta
print(tim)
# => 105.06054258346558


time_sta = time.time() # 時間計測用
# rayを使って並行実行する
future_ids = []
for i in range(10):
    future_ids.append(tarai.remote(13, 7, 0))
# 全ての処理が終了するまで待つ
for fi in future_ids:
    ray.get(fi)
time_end = time.time()
tim = time_end- time_sta
print(tim)
# => 17.274834156036377
