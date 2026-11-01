import pymysql

# pymysql.install_as_MySQLdb() 的作用是将 PyMySQL 的接口伪装成 MySQLdb 的接口。
# 这样，一些依赖于 MySQLdb 的代码（例如某些旧的框架或库）可以直接使用 PyMySQL 而无需修改代码。
pymysql.install_as_MySQLdb()  # django默认模式MySQLdb连接数据库
