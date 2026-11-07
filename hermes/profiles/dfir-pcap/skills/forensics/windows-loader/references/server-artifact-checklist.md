# 服务器工件清单

这是检查表，不是命令序列。没有第二来源时，结论降为待核验。GE-BootMagix 未接入，不要调用 create-vm。未接入，不要调用 clonezilla-to-e01。不能把“如果仿真会看到”写成检材事实。

## Windows

- 事件日志：Security、System、Application、PowerShell、RDP、任务计划、服务安装。
- 持久化：服务项、计划任务、启动项、注册表 Run 键、WMI、远程管理配置。
- 业务痕迹：IIS、MSSQL、文件共享、远程桌面、PowerShell 记录、本地账户变化。

## Linux

- 日志：`auth`、`syslog`、`journal`、`messages`、Web 和数据库日志。
- 持久化：`sshd_config`、`sudoers`、`cron`、`systemd` 单元、启动脚本。
- 业务痕迹：nginx、Apache、MySQL、PostgreSQL、Redis、Tomcat、shell 历史。

## 交叉

登录、配置变化、进程启动、服务重启和外联要能对上时间线。IP、端口、账户、进程和文件路径一起核对。单一来源只写“待核验”。未观察到写成未检查或本次未发现，不写成不存在。
