rem del build /Q /S /F
del dist /Q /S /F
call %~dp0\environment\ttr_retr\Scripts\activate.bat
python setup.py py2exe
xcopy %~dp0cacert.pem %~dp0dist\
xcopy %~dp0init_client.bat %~dp0dist\

del build /Q /S /F
rmdir build
"C:\Program Files (x86)\7-Zip\7z.exe" a -tzip "dist.zip" "dist"