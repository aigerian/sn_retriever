set mh=c:\mongo
set rh=c:\redis
start %mh%\bin\mongod.exe -dbpath=%mh%\db\ -logpath=%mh%\logs\server.log -logappend -noauth -port=27017 --diaglog=3 --setParameter textSearchEnabled=true
start %mh%\bin\mongod.exe -dbpath=%mh%\db_duplicate\ -logpath=%mh%\logs\server_duplicate.log -logappend -noauth -port=27018 --diaglog=3 --setParameter textSearchEnabled=true
start %rh%\bin\redis-server.exe
