# Запускаемые комманды.
Перед тем как запустить обработку с помощью какой-либо из walker"ов следует запустить его с параметром -h.
Ничего страшного не произойдет, а программа напишет в понятном виде как ей пользоваться.

## Параметры для walker_ttr
```
  -h, --help            show this help message and exit
  -l LIST, --list LIST  load list of user ids you must provide file of this
                        list
  -u USER, --user USER  load one user name
  -rt RELATION_TYPE, --relation_type RELATION_TYPE
                        using specific relation type, as default using
                        'friends', you can use 'followers'
  -d DEPTH, --depth DEPTH
                        depth of social (friends and followers) and saving
                        users relations
```

## Параметры для walker_vk

```
  -h, --help            show this help message and exit
  -l LIST, --list LIST  load list of user ids you must provide file of this
                        list
  -u USER, --user USER  load user id
  -r, --recursive       will load social siblings of retrieved users
```

У обоих можно указать либо отдельного пользователя либо списком в предоставленном файле. 
Следует обратить внимание на пользователей вконтакте - требуется именно идентификаторы пользователей. 

# Визуализация 
Для отправки в Gephi потребуется сачала нстроить его. Это легко. Нужно скачать [его](http://gephi.github.io/) и установив его 
поставить плагин GraphStreaming: Сервис -> Подключаемые модули -> Доступные подключаемые модули  
![alt скрин установки плагина]() 
Установив этот плагин переходим в его вкладку и включаем сервер принимающие данные: Окно -> Streaming
![alt скрин включения сервера]()

# Инструкция
0. Если уже имеются наработки и есть данные в БД, извлеченные при помощи walker_ttr то следует выполнить 

```
python update.py
```
Для обновления этих данных, дабы они были совместимы с последующими извлечениями. 

1. Установить python версии 2.7.6. (active state)
  * Настроить виртуальное окружение выполнив команду 
```
virtualenv <путь где оно будет хранится>
```
  * Применить виртуальное окружение командой 
```
cmd /k <путь где оно хранится>\Scripts\activate.bat 
```
  * Успешным результатом применения будет подпись перед вводом приглашения командной строки, к примеру, так:
```
(venv) C:\>
```
  * Далее в этой инструкции, если требуется выполнить команду в виртуальном окружении, то будет пометка: (venv). Виртуальное окружение требуется для того чтобы в дальнейшем не возникало конфликтов python библиотек. 

2. Установить git и склонировать проект, выполнив команду: 
```
git clone http://github.com/alexeyproskuryakov/ttr_retr 
```
Для копирования исходных кодов проекта. И перейти в папку с проектом (выполнить команду cd ttr_retr).

3. Для установки необходимых библиотек. В примененном виртуальном окружении выполнить команду: 
```
(venv) pip install -r requirements.txt 
```

> Могут возникнуть проблемы с установкой библиотек lxml, numpy (точнее с их компиляцией). В таком случае, с сайта http://www.lfd.uci.edu/~gohlke/pythonlibs/ можно скачать ее скомпилированную версию (под версию python 2.7.6) и установить как обычную windows программу. После, для добавления ее в виртуальное окружение просто скопировать из корневого python окружения в созданное ранее виртуальное, т.е. скопировать папку lxml из c:\python27\lib\site-packages в <путь где хранится созданное виртуальное окружение>\lib\site-packages\.
Вообще, на вышеуказанном сайте можно скачать почти все платформозависимые библиотеки для python. 

  * Либо установить библиотеки последовательно:
```
pip install pymongo redis requests
```

4. Скачать и установить базы данных: 
  * MongoDB - скачать с оффициального сайта www.mongodb.com/downoloads и установить.
После скачивания извлечь из архива содержимое, к примеру, в c:\mongo. Для просмотра содержимого БД рекомендуется использовать бесплатное приложение robomongo 
  * Redis - скачать с официального сайта www.redis.io/downloads и извлечь из архива содержимое, к примеру, в c:\redis.

5. В проекте имеется уже созданный bat файл для запуска серверов обоих БД с названием 
```
start_environment.bat
```
6. Для запуска системы извлечения данных из какой-либо социальной сети в корне проекта имеется файл с названием 
```	
walker_<имя социальной сети>.py <ник_пользователя> <тип_связи> 
```
 В параметрах следует указать: 
  * Ник пользователя с которого следует начинать обход. 
  * Тип связи по которому будут происходить переходы (опционально, по умолчанию friends)
 
> К примеру, если выполнить
```
	(venv) python walker_ttr.py medvedevrussia followers 
```
> Система начнет извлекать данные пользователей и их сообщения начиная с Дмитрия Медведева, передвигаясь по его подписчикам. И сохранять извлеченные данные в mongoDB в коллекцию users. Поля записей могут отличатся в зависимости от социальной сети, но все схожи полями: 
	sn_id - идентификатор в социальной сети
	update_date - время когда были извлечены данные
	screen_name - ник пользователя
	и прочее.
	
8. Система слежения представлена файлами: 
```
	tracker_<имя социальной сети>.py 
```
   Для ее работы требуется иметь в БД уже извлеченные данные пользователей, флагом является поле update_date ранее которого будет извлекаться данные. Для запуска системы следует выполнить команду: 

```
	(venv) python tracker_<имя социальной сети>.py  
```

  * В параметрах можно указать время после которого следует следить за пользователем в секундах. Если его не указывать, то система возьмет это значение из файла properties.py

# Описание извлекаемых данных.

В зависимости от социальной сети извлекаются 4 типа объектов: User, Message, SocialObject, ContentObject. Каждый из которых хранится в своей коллекции в MongoDb. Связи между двумя пользователями либо между пользователем и группой (для социальной сети vk), ввиду их большого количества хранятся в Redis, для последующего быстрого извлечения. 
Из Twitter извлекаются только объекты User и Message, из vk - все 4 типа.


## Объекты.
### *User* 
Характеризует пользователя социальной сети. Находятся в коллекии users и имеют различные поля в зависимости от ресурса. Однако, имеются и схожие поля: 

	1. source - собственно имя ресурса (ttr - твиттер, vk - вконтакте, fb - фейсбук)
	2. name и <[first, last, middle]>_name - имя пользователя, который он указал при регистрации
	3. sn_id - идентификатор пользователя в социальной сети
	4. status - последнее его сообщение (либо его состояние, которое он указал в графе "Что с вами происходит?")
	5. birthday - дата рождения
	6. screen_name - ник
	7. update_date - время сохранения в БД и время последнего просмотра 
	8. [followers, friends]_count - количество подписчиков и друзей пользователя соостветственно 
	9. verified - провереный ли пользователь. В некоторых случаях это ответ на email посланный при регистрации, в иных проверка модератором, на реальность имени и прочего.
	
### User из Twitter. 

Имеются следующие поля:

	1. follow_request_sent - отправленн ли запрос на подписку этому пользователю (true/false)
	2. profile_use_background_image - используется ли картинка в качестве фона в профайле пользователя
	3. time_zone - временная зона
	4. update_date - время последнего обращения системы к данным этого пользователя
	5. is_translator - принадлежит ли пользователь к сообществу переводчиков twitter
	6. protected - пользователь скрывает свои твиты, твиты показываются только его друзьям и подписчикам
	7. listed_count - количество публичных листов в которых состоит данный пользователь
	8. status - текущий статус пользователя (последнее сообщение):
  		*  favorited - в избранном ли этот статус у бота
  		*  text - текст статуса
  		*  favorite_count - количество пользователей кто добавил этот статус себе в избранное
  		*  lang - язык текста
  		*  created_at - когда создан статус
  		*  retweeted - был ли он переслан
  		*  coordinates - координаты места где был сделан статус
  		*  source - ресурс с которого был создан статус
  		*  retweet_count - количество пересылок (репостов) статуса
  		*  entities - сущности (которые есть также в сообщениях). Все атрибуты этого объекта являются массивами, и 	каждый элемент есть объект который содежит информацию о позиции в тексте:
			*    symbols : массив символов
    			*    user_mentions : массив пользователей упоминаемых в тексте статуса
    			*    hashtags : массив хэштегов 
    			*    urls : массив ссылок
	9. lang - основной язык пользователя
	10. utc_offset - смещение по времени
	11. statuses_count - количество статусов (сообщений пользователя)
	12. description - то что пользователь написал о себе
	13. geo_enabled - индикатор того позволил ли пользователь вставлять в свои твиты гео-теги
	14. profile_background_tile - узор фона
	15. favourites_count - количество избранных объектов у пользователя
	16. url - ссылка которую указал пользователь в своем описании
	17. created_at - когда был создан аккаунт
	18. default_profile - настроил ли пользователь свой аккаунт (дополнительной индивидуальностью, к примеру картинкой в фоне)
	19. following - читает ли текущий бот искомого пользователя



## User из vkontakte (vk).

	* sex - возвращаемые значения: 1 - женский, 2 - мужской, 0 - без указания пола. 
	* city - выдаётся id города, указанного у пользователя в разделе "Контакты". Название города по его id можно узнать при помощи метода getCities. Если город не указан, то при приёме данных в формате XML в узле <user> отсутствует тег city. 

	* country - выдаётся id страны, указанной у пользователя в разделе "Контакты". Название страны по её id можно узнать при помощи метода getCountries. Если страна не указана, то при приёме данных в формате XML в узле <user> отсутствует тег country. 
	* online - показывает, находится ли этот пользователь сейчас на сайте. Поле доступно только для метода friends.get. 
Возвращаемые значения: 1 - находится, 0 - не находится.  
Если пользователь использует мобильное приложение либо мобильную версию сайта - будет возвращено дополнительное поле online_mobile. 
	* lists - список, содержащий id списков друзей, в которых состоит текущий друг пользователя. Метод получения id и названий списков: friends.getLists. Поле доступно только для метода friends.get. Если текущий друг не состоит ни в одном списке, то при приёме данных в формате XML в узле <user> отсутствует тег lists. 
	* screen_name - возвращает короткий адрес страницы (возвращается только имя адреса, например andrew). Если пользователь не менял адрес своей страницы, возвращается 'id'+uid, например id35828305. 
	* has_mobile - показывает, известен ли номер мобильного телефона пользователя. 
Возвращаемые значения: 1 - известен, 0 - не известен. 
Рекомендуется перед вызовом метода secure.sendSMSNotification. 
	* contacts - возвращает поля:
  	* mobile_phone мобильный телефон пользователя 
  	* home_phone домашний телефон пользователя
	* education - возвращает код и название университета пользователя, а также факультет и год окончания.  
	* universities - список высших учебных заведений, в которых учился текущий пользователь. 
	* schools - список школ, в которых учился текущий пользователь. 
	* can_post - разрешено ли оставлять записи на стене у данного пользователя. 
	* can_see_all_posts - разрешено ли текущему пользователю видеть записи других пользователей на стене данного пользователя. 
	* can_write_private_message - разрешено ли написание личных сообщений данному пользователю. 
	* activity - возвращает статус, расположенный в профиле, под именем пользователя 
	* last_seen - возвращает объект, содержащий поле time, в котором содержится время последнего захода пользователя. 
	* relation - возвращает семейное положение пользователя: 
	  * 1 - не женат/не замужем 
	  * 2 - есть друг/есть подруга 
	  * 3 - помолвлен/помолвлена 
	  * 4 - женат/замужем 
	  * 5 - всё сложно 
	  * 6 - в активном поиске 
	  * 7 - влюблён/влюблена 

	* counters - возвращает количество различных объектов у пользователя. Поле возвращается только в методе getProfiles при запросе информации об одном пользователе. Данное поле является объектом, который содержит следующие поля:
	  * albums - количество фотоальбомов
	  * videos - количество видеозаписей
	  * audios - количество аудиозаписей
	  * notes - количество заметок
	  * friends - количество друзей
	  * groups - количество сообществ 
	  * online_friends - количеcтво друзей онлайн
	  * mutual_friends - количество общих друзей (если запрашивается информация не о текущем пользователе)
	  * user_videos - количество видеозаписей с пользователем
	  * followers - количество подписчиков

	> Если запрашивается информация не о текущем пользователе, то отсуствие полей friends, online_friends, mutual_friends, user_photos в объекте означает, что информация по ним скрыта соотвествующими настройками приватности у запрашиваемого пользователя. Если при запросе данного поля оно отсутствует в ответе, то это означает, что текущий пользователь находится у запрашиваемого пользователя в черном списке. 
	
	* wall_comments - разрешено ли комментирование стены. Если комментирование стены отключено - то комментарии на стене не отображаются. 
	* relatives - возвращает список родственников текущего пользователя, в виде объектов, содержащих поля uid и type. type может принимать одно из следующих значений: grandchild, grandparent, child, sibling, parent. 
	* interests, movies, tv, books, games, about - позволяют получить профильную информацию о пользователе.  
	* connections - позволяет получить информацию о аккаунтах пользователя на других сервисах. При указании этого поля будут приходить следующие ключи в случае наличия соответствующих записей: twitter, facebook, facebook_name, skype, livejounal.


## ContentObject 

Понимаются некоторые контентные объекты такие как фотографии, видео, обсуждения групп. Все эти объекты имеют различные наборы атрибутов в зависимости от типа обхекта, а также к каждому из них могут привязываться Message посредством информации из атрибута comment_for. Также для каждого такого объекта определены слеующие поля:

	* 'sn_id': '%s_video_%s' % (el.get('id') or el.get('vid'), el['owner_id']), # уникальный идентификатор записи 
        * 'user': # ссылка на пользователя загрузившего эту запись
	* 'text':  # что пользватель написал про эту запись
	* 'created_at':  # когда была создана
        * 'views_count':  # количество просмотров, в некотором случае
        * 'comments_count':  #количество комментариев
        * 'likes_count': #количество лайков
        * 'video_id': #идентификаторы этого контента в сети vk
        * 'photo_id': #
        * 'wall_post_id': #
        * 'type':  #тип [wall_post, video, photo,]
        
        
## SocialObject 

Представляют соединения пользователей такие как: группы, публичные страницы, встречи и различаются свойством type.

Для каждого объекта SocialObject определены следующие поля:

	* sn_id - иеднтификатор группы, страницы, встречи в социальной сети vk в некоторых случаях умесно его применять в обратном значении, таким как get_photos	
	* private - закрыта ли это соединение для сторонних пользователей (чтобы вступить требуется отправить запрос адиминистратору этого соединения)
	* name - видное всем пользователям имя соединения.
	* screen_name - "ник" группы
	* type - тип соединения (может быть group, page, event)
	* source - всегда равен vk


# Связи. 

Связь есть тройка оъектов состоящая из идентификаторов начального  пользователя и конечного  пользователя либо группы и типа связи. Связи с индикаторами пользователей социальной сети twitter имеют только 2 типа freind и follower. Связи с идентикиторами пользователей социальной сети vk добавляют в множество типов связей twitter еще и 'friend', 'follower', 'like', 'comment', 'mentions' между пользователями и 'member', 'admin', 'subscribe', 'request', 'invitation' между группами. 

-может быть их разделить?


