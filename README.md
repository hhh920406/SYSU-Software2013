#C.A.S.T designer
iGEM-SOFTWARE-2013
==================
This is the project of igem 2013 by SYSU-Software.

## Introduction
Accurate simulation and gene circuit design are essential but difficult parts in synthetic biology.Here, we designed CAST to cover the workflow from beginning to end, users can focus on function design and the gene circuit would be automatically designed. Furthermore, we developed a new simulation model that work with standard dynamic characteristic and verified by wetlab experiments. Moreover, we build an expandable database that users can contribute their own dynamic information which would lead to more accurate and sufficient dynamic information of all the Biobricks. Finally, our software is designed as an easy deployed server so that it can be used on personal purpose or shared by a whole lab or institution. 

## Supported OS
* Windows XP or higher
* Mac OS X
* Linux

## Installation Guide
For Windows users, to start using CAST designer, you need to enter `project`
directory and choose 32-bit or 64-bit version of python. Our bat file in
`python` directory will automatically start the server and you can run CAST
designer locally on your computer.

For unix-like operating system users, you may need to confirm that all the
dependencies all correctly installed on your computer. You shall have your `pip`
installed on your computer, and then use `pip` to install other dependencies.  
The following commands shows how to install these requirements in ubuntu.
```
sudo apt-get install pip
sudo pip install -r requirements.txt
```

## Detail
We use pure javascript to implement the front end,and use flask framework (especially the websocket protocol for data transfer)for the back end,which is written in python.Next we use sqlite as the database.By the way,we have provided a brower so called cefsharp,which is base on chromium core and written in c#

## Safety
We have used rsa algorithm to encrypt any password transferation,and use sha-a algorithm for information digesting,never save plain password.

## License
This project is released under MIT License. See LICENSE for the content.
