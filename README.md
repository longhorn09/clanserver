# clanserver

## Setup instructions 
```
sudo apt-get install python-pip python-dev build-essential
sudo pip install --upgrade pip
sudo pip install gevent
sudo pip install xmltodict
python clanserver.py
```


If you want to run the server with persistence
```
nohup python clanserver.py &
```

## Troubleshooting

Open up port 3000 in your inbound security rules within the Amazon EC2 security groups console.

```
sudo ufw allow 3000/tcp
```

## History

Original version written in Java.  
Then ported to C#.NET  
Ported to Python by [sswang923](https://github.com/sswang923)  

## Credits

[sswang923](https://github.com/sswang923)
