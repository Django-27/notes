# 镜像、容器、仓库
镜像：操作系统分为内核和用户空间，对于 Linux 启动后，会挂载 root 文件系统为其提供用户空间支持；
Docker 镜像（Image）是一个特殊的文件系统，除了提供容器运行时所需的程序、库、资源、配置等文件外，
还包含了一些为运行时准备的一些配置参数（如匿名卷、环境变量、用户等），但不包含任何动态数据，其
内容在构建之后也不会被改变。
容器：是镜像运行的实体，可以创建、启动、停止、删除、暂停等，实质是进程，运行于属于自己的独立的
命名空间，即容器可以拥有自己的 root 文件系统、网络配置、进程空间等；
仓库：每一个仓库可以包含多个标签 Tag，每一个标签对应一个镜像；格式：<仓库名>：<标签>

查看系统种类： cat /etc/*-release 和 uname -a
检查 docker 状态：systemctl status docker
测试是否安装正确 docker run --rm hello-world
安装自动补全：yum install bash-completion 
检查信息：docker info

-it -i 表示交互式操作，-t 表示终端
--rm 表示容器退出后将其删除
列出顶层镜像：docker image ls
查看镜像、容器、数据卷所占用的空间: docker system df
虚悬镜像: docker image ls -f dangling=true 和清理 docker image prune 或 docker iamge rm
```  cat /etc/docker/daemon.json
{
    "registry-mirrors": [
        "https://dockerproxy.com"
    ]
}

systemctl daemon-reload
systemctl restart docker

docker pull dockerproxy.com/library/nginx:latest
```

# Dockerfile
```
FROM nginx
RUN echo '<h1>Hello, Docker!</h1>' > /usr/share/nginx/html/index.html
```
FROM 指定基础镜像，必须是第一个指令，且必须存在；
FROM scratch 是一个特殊镜像，名为 scratch，表示是一个空白的镜像；

构建：docker build -t nginx:v3 .
测试：docker run nginx:v3 /bin/echo 'Hello world'
注意 . 表示当前目录，即上下文路径；上下文是构建镜像时 Docker 引擎用来查找 Dockerfile 和相关文件的路径；
上下文不仅包括 Dockerfile 文件本身，还包括 Dockerfile 所在的目录以及在构建过程中被引用的其他文件和目录；
Dockerfile 文件所在的目录会在构建的时候发送给守护进程（服务端），不想发送的文件添加到 .dockerignore 中；

启动并进入交互：docker run -ti nginx:v3 /bin/bash
退出后查看正在运行的容器：docker ps
docker run 后的执行步骤：
```
- 检查本地是否存在指定的镜像，不存在就从 registry 下载
- 利用镜像创建并启动一个容器
- 分配一个文件系统，并在只读的镜像层外面挂载一层可读写层
- 从宿主主机配置的网桥接口中桥接一个虚拟接口到容器中去
- 从地址池配置一个 ip 地址给容器
- 执行用户指定的应用程序
- 执行完毕后容器被终止
```
参数：-d 以守护态运行
停止：docker container stop 容器
进入容器：docker exec -it 容器 /bin/bash

# Dockerfile 指令
1 将构建上下文中的文件复制一份到镜像内目标路径 COPY package.json /usr/src/app/ 
源文件的各种元数据也会保留，如读写执行权限、文件变更时间、git信息
添加 --chown=<user>:<group> 选项来改变文件所属的用户和组
2 ADD 与 COPY 基本一致，增加了支持 URL，下载后权限为600，如果权限不对，可以用 RUN 调整
一般约定仅需要自动解压的场合使用 ADD
3 CMD 用于指定默认的容器主进程启动时的命令 CMD ["nginx", "-g", "daemon off;"] 
4 ENTRYPOINT 的格式和 RUN 指令格式一样，分为 exec 格式和 shell 格式;
可以实现让镜像变成命令一样使用、完成应用运行前的准备工作
5 ENV 设置环境变量
6 VOLUME 定义匿名卷， VOLUME /data
7 EXPOSE 暴露端口
8 WORKDIR 指定工作目录， WORKDIR /app
9 USER 指定当前用户
10 HEALTHCHECK 健康检查， HEALTHCHECK --interval=5s --timeout=3s CMD curl -fs http://localhost/ || exit 1



