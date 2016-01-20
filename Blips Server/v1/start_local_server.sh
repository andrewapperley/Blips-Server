#!/bin/bash

source /home/admin-account/api/blips_server/blips_environ/bin/activate
sudo killall -9 python
cd /home/admin-account/api/blips_server/Blips\ Server/v1
sudo nohup python application.py &