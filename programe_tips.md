# Redis 
## 1 常用数据类型 
- 字符串(strings/string)、散列(hashes/hash)、列表(lists/list)、集合(sets/set)、有序集合(sorted sets/zset)；bitmaps、hyerloglogs、geospatial地理空间、Streams消息
  - SDS 可动态扩展内存、二进制安全、与传统的C语言字符串类型兼容
    - 在C语言中，字符串是以’\0’字符结尾（NULL结束符）的字符数组来存储的，通常表达为字符指针的形式（char *）。它不允许字节0出现在字符串中间，因此，它不能用来存储任意的二进制数据
    - 不以字符’\0’来标识字符串的结束，而是单独一个字段记录长度信息
  - ziplist 是一个经过特殊编码的双向链表、为了提高存储效率
    - 用于存储字符串或整数，其中整数是按真正的二进制表示进行编码的，而不是编码成字符串序列。它能以O(1)的时间复杂度在表的两端提供push和pop操作
    - 一个普通的双向链表，链表中每一项都占用独立的一块内存，各项之间用地址指针（或引用）连接起来。这种方式会带来大量的内存碎片，而且地址指针也会占用额外的内存。而ziplist却是将表中每一项存放在前后连续的地址空间内，一个ziplist整体占用一大块内存。它是一个表（list），但其实不是一个链表（linked list）
    - 对于值的存储采用了变长的编码方式，大概意思是说，对于大的整数，就多用一些字节来存储，而对于小的整数，就少用一些字节来存储
  - quicklist 确实是一个双向链表，而且是一个ziplist的双向链表；quicklist的每个节点都是一个ziplist
  - skiplist 首先是一个有序链表，在有序链表的基础上发展起来；
    - 受这种多层链表的想法的启发而设计出来的，上面每一层链表的节点个数，是下面一层的节点个数的一半，这样查找过程就非常类似于一个二分查找
    - 指的就是除了最下面第1层链表之外，它会产生若干层稀疏的链表，这些链表里面的指针故意跳过了一些节点（而且越高层的链表跳过的节点越多）
    - skiplist上进行范围查找就非常简单，只需要在找到小值之后，对第1层链表进行若干步的遍历就可以实现
    - 平衡树的插入和删除操作可能引发子树的调整，逻辑复杂，而skiplist的插入和删除只需要修改相邻节点的指针，操作简单又快速
  - intset 为了实现集合(set)这种对外的数据结构，它包含的元素无序，且不能重复，基础的集合并、交、差的操作
    - 当set中添加的元素都是整型且元素数目较少时，set使用intset作为底层数据结构，否则，set使用dict作为底层数据结构

- String 可以是 int/embstr/raw，Hash 可以是 ziplist/hashtable，List 可以是 quicklist/ziplist，Set 可以是 hashtable/intset，Sorted Set 可以是 ziplist/skiplist

- Redis 快的原因，首先是基于内存；Redis 整个结构类似 HashMap，查找和操作的复杂度都是 O(1)，不需要磁盘IO或者全表扫描；Redis 处理是单线程，
  避免了多线程的上下文切换和线程竞争造成的开销； 底层采用 select/epoll 多路复用高效非阻塞IO模型；
- select、poll、epoll之间的区别
  - select 时间复杂度 O(n)，当有 IO 事件发生了，并不知道是哪个或那几个流，需要轮询 fd，找出能够读出或写入的流，轮询时间长
  - poll 时间复杂度 O(n)，解决了 select 最大连接数的限制，基于链表存储 fd (select 是基于 bitmap, 二进制字符串)
  - epoll 时间复杂度 O(1)，通过事件通知的方式，每个事件与 fd 进行关联
  - 都是i/o多路复用的机制，监视多个socket是否发生变化，本质上都是同步i/o
    select,poll实现需要自己不断轮询所有监测对象，直到对象发生变化，在这个阶段中，可能要睡眠和唤醒多次交替，
    虽然都会睡眠和唤醒，但是select和poll在被唤醒的时候要遍历整个监测对象集合，
    而epoll只要判断就绪链表是否为空即可，节省了大量cpu的时间

- 缓存雪崩是由于大量的热点 Key 在同一时间全部失效，请求直接进行 DB 查询，可以对过期时间进行错开设置、永不过期、使用分布式锁或者 MQ 使得请求串行，如果已经发生，亦可以通过提前配置本地缓存，或者调整 Hystrix 限流策略，并且提前开启 RDB(快照) + AOF(持久化命令) 持久化，重启 Redis 时会从磁盘加载数据完成快速恢复；
    - 步骤：如果和时间点无关的数据，可以采用给 key 加随机过滤时间；如果和时间点有关，加随机时间可能会读取到脏数据，可以用击穿的解决办法，线程去更新 key，其他请求做延迟，睡几十毫秒或者几秒；

- 缓存穿透是在异常情况下，缓存和数据库中都没有数据，用户如果不断发起请求，每次请求都会打到数据库上面，造成数据库的压力过大或者无响应，比如用户 Id 都是从1开始的，但是数据校验没有拦截，请求了一个不存在的-1，即后端一定要校验前端传递的数据，不合法立即返回；也可以将不存在的 key 缓存为 null，并且设置一个过期时间；还可以添加布隆过滤器，如果不存在直接返回，存在的话再去查询数据库并更新缓存最后返回；
    - 客户端实现布隆滤波器或者使用 redis 中布隆滤波器

- 缓存击穿（凿了一个孔）是指一个热点 Key 失效瞬间，持续大量请求直接打到数据库上，就好像在一个完好无损的桶上凿开了一个洞；可以设置热点数据永不过期，定时任务去刷新缓存；也可以在第一请求去查询数据库的时候对他添加一个互斥锁，其余请求都会被阻塞，直到锁释放，后面的请求拿到缓存数据，但是会阻塞线程，造成系统吞吐量下降；
    - 步骤：用 setnx() 设置锁，即 key 不存在的时候设置，防止重复加锁；拿到锁喉去数据库中取数据，返回后释放锁；
    - 问题：为防止拿锁后的处理挂掉，可以设置过期时间；拿锁的处理超时还未返回，通过再开启一个线程进行监控，适当延长过期时间；
    - 命令要用 set key value nx px，他是原子的，value要具有唯一性;释放锁时要验证value值是否相等，不能误解锁
    - 在Redis的master节点上拿到了锁;但是这个加锁的key还没有同步到slave节点;master故障，发生故障转移，slave节点升级为master节点;导致锁丢失
    - 解决上面的问题：Redlock算法
    - SETNX 是SET IF NOT EXISTS的简写.日常命令格式是SETNX key value，如果 key不存在，则SETNX成功返回1，如果这个key已经存在了，则返回0

- 缓存淘汰策略：volatile_lru 最近最少使用；volatile_ttl 从设置过期时间的数据中挑选 ttl 值越大的数据；volatile-random 从设置过期时间的数据中任意挑选进行淘汰；allkeys-lru 从数据集中进行挑选；allkeys-random 从数据集中任意挑选；no-envication 默认策略，内存不足以容纳新增是，新写入操作会报错，可以保证已有的数据不丢失；
- 删除策略有，定时删除，检查 key 的过期时间，创建一个定时器，时间到了立即删除；惰性删除，过期不管，但取值的时候会判断是否过期，如果过期就删除，没有过期就返回值；定期删除，每隔一段时就对数据库进行检查，删除里面过期的数据

- Redis 真的是单线程的吗
Redis6.0 之前是单线程的，Redis6.0 之后开始支持多线程;redis 内部使用了基于epoll的多路复用IO非阻塞，也可以多部署几个redis 服务器解决单线程的问题；redis 主要的性能瓶颈是内存和网络；执行命令的核心模块还是单线程的

- Redis 通过 config set requirepass 123 设置密码，auth 123 验证密码

- 消息的顺序性
    - 某些场景需要保证消息的顺序性，一旦出现乱序会造成业务逻辑的错误执行，给业务费造成损失
    - 列表 LPUSH/RPOP 先进先出满足对数据的存取；BRPOP 命令，也称为阻塞式读取，客户端在没有读取到队列数据时，自动阻塞；
- 消息的幂等性
    - 重复消费消息，如果由于网络阻塞发生消息重传，消费者会多次收到重复消息
    - 给每一个消息增加一个全局唯一的 ID，消费者记录下来，判断这个消息是否进过了处理
- 消息的可靠性
    - 消费者在处理消息的时候出现异常，或者宕机，重启后，要能重新读取消息再进行处理，否则会有遗漏
    - PRPOPLPUSH 命令，消费者从 List 中读取消息，同时 Redis 会把这个消息插入到另一个 List（也叫做备份 List）中保存；
      如果消费者读取到的消息没有能正常处理，其重启后就可以充备份 List 中重新读取消息并处理

- 基于 Redis Stream，是专门为消息队列设计的数据类型
    - XADD 插入消息，保证有序，可以自动生成全局唯一 ID
        - xadd mqstream * repo 5  # 向名称为 mqstream 的消息队列中插入一条消息，key 是 repo，值是5，* 标识自动生成全局唯一 ID，是一个毫秒级的时间戳及一个序列（"1676380878957-0"）
    - XREAD 读取消息，可以按 ID 读取数据
        - xread block 100 streams mqstream 1676380878957-0
        - xread block 100 streams mqstream $  # $ 标识读取最新消息，超过阻塞时间返回 nil 空值
    - XREADGROUP 按照消费组读取消息
    - XPENDING 查询消费组中已读取但是尚未确认的消息
    - XACK 用于向消息队列确认消息已经处理完成
- Redis 的事务
    - 先以 MULTI 开始一个事务， 然后将多个命令入队到事务中， 最后由 EXEC 命令触发事务， 一并执行事务中的所有命令。如果想放弃这个事务，可以使用DISCARD 命令
    - 上面这种事务不支持回滚；对比 MySQL 的事务，要么全部执行，要么全部不执行
    - 当执行事务报错的时候，之前已经成功的
    - 命令并没有被回滚，也就是说在执行事务的时候某一个命令失败了，并不会影响其他命令的执行，即 Redis 的事务并不会回滚
    - Redis Watch 命令对一个或多个 key 的进行监视，Unwatch 命令用于取消
      - 如果在事务执行之前这个(或这些) key 被其他命令所改动（如开启的另一个终端中），那么事务将被打断并回滚到之前的状态，
      - 即事务中所有命令都未执行（CAS compare and swap 乐观锁）
- Redis 如何实现分布式锁
  - set key value ex nx
  - 当 key 不存在时，将 key 的值设为 value ，返回 1。若给定的 key 已经存在，则 set nx 不做任何动作，返回 0
  - 当 set nx 返回 1 时，表示获取锁，做完操作以后 del key ，表示释放锁，如果 set nx 返回 0 表示获取锁失败
  - 为什么不先 set nx ，然后再使用 expire 设置超时时间
    - 我们需要保证 set nx 命令和 expire 命令以原子的方式执行，否则如果客户端执行 set nx 获得锁后，这时客户端宕机了
    - 那么这把锁没有设置过期时间，导致其他客户端永远无法获得锁了；即要写成一行的形式
- memcached 与 redis 的区别
  - redis提供数据持久化功能，memcached无持久化；
    redis的数据结构比memcached要丰富，能完成场景以外的事情；
    memcached的单个key限制在250B，value限制在1MB；redis的K、V都为512MB;当然这些值可以在源码中修改；
    memcached数据回收基于LRU算法，Redis提供了多种回收策略（包含LRU），但是redis的回收策的过期逻辑不可依赖，没法根据是否存在一个key判断是否过期。但是可根据ttl返回值判断是否过期；
    memcached使用多线程，而redis使用单线程，基于IO多路复用实现高速访问。所以可以理解为在极端情况下memcached的吞吐大于redis。
    - 结论：
    普通KV场景：memcached、redis都可以。
    从功能模块单一这个角度考虑的话，推荐memcached，只做cache一件事。
    在KV长度偏大、数据结构复杂（比如取某个value的一段数据）、需要持久化的情况下，用redis更适合：但是在使用redis的时候单个请求的阻塞会导致后续请求的积压，需要注意

# redis 与 mysql 数据一致性问题
一般情况下，mysql存储业务数据，redis作为缓存，二者配合提高程序响应
- 在更新数据库数据时，需要同步redis中缓存的数据，所以存在两种方法：
    第一种方案：先执行update操作，再执行缓存清除
    第二种方案：先执行缓存清除，再执行update操作
- 在极端情况下，可能会出现数据不一致的情况
   可以采用延迟双删策略，先进行缓存清除，再执行update，最后（延迟N秒）再执行缓存清除，延迟时间一般是 大于一次写redis操作的时间，一般为3-5秒
   也可以采用监听mysql binlog，然后去更新redis，是一种最终一致性的策略

# cookie / session / token
HTTP 是无状态的，一次请求结束断开连接，下一次请求无法判断这个请求的用户
- cookie 保存在客户端
  - 浏览器自身实现的一种数据存储功能；由服务器生成，发送给浏览器进行保存到某个目录下得文件内，下一次请求同一个网站是会把该 cookie 发送给服务器
  - 浏览器保证 cookie 不会被恶意使用，不会占用太多空间，每个域都有限制；如果没有指定过期时间，那么当前 session 期间内有效，当前 session 会话结束也就过期了；对应关闭浏览器中该页面，此 cookie 也就被删除了；
- session 保存在服务端
  - 我们和别人的交谈就是一个会话，服务器为每个客户端分配不同的身份标识，客户端每次请求都会带上这个身份标识；
- token 存储在服务端
  - 可以是一个 UUID 字符串，也可以是用户 ID 进过加密的字符串；
      - 前端通过登录获取 token，每次请求都带着，后端收到后延长过期时间
      - 如果很久没有使用，导致 token 过期，可以返回指定的状态码，前端跳转到登录页面
(1) 数据存储位置不同，cookie 存在客户端，session 存在服务器
(2) 安全程度不同，cookie 存客户端本地，分析 cookie，实现 cookie 欺骗，考虑到安全性，所以用 session
(3) 性能不同，session 存服务器，访问量大时，会增加服务器负载，考虑到性能，所以用 cookie
(4) 数据存储大小不同，单个 cookie 不超过 4k，部分浏览器会限制 cookie的存储个数，但 session 存在服务器，故不受客户端浏览器限制

# get / post
- GET 请求，参数用 ？ 连接在 url 之后，只能以文本的形式进行传递；数据量小，4kb 左右；安全性低，会将信息显示在地址栏；速度快；从服务器获取资源；浏览器会进行缓存；
- POST 请求，相对于 get 安全性高；传递数据量大；向服务器发送数据；数据放在 body 中；浏览器不会缓存；

# 网络传输模型 
HTTP 超文本传输协议 （Hypertext Transfer Protocal），早期的计算机只能传递本地的文本文件，后来可以传递图片、音频、视频，还有超链接跳转
网络的五层结构，包含物理层、链路层、网络层、传输层、应用层

- 应用层是应用程序和网络协议存放的分层，web 用的 HTTP，电子邮件传输协议 SMTP，端系统文件上传协议 FTP，域名解析 DNS 协议；信息分组是报文；
- 传输层负责在应用之间传递报文，主要有 TCP 、UDP；前者面向连接，能控制并确认报文是否到底，提供拥塞机制控制网络传输（滑动窗口），当网络拥塞时，会抑制其传输速率；后者提供无连接，不具备可靠性，没有拥塞控制；传输层的分组成为报文段（segment）
- 网络层负责将数据报（datagram）从一台主机移动到另一台主机，非常重要的协议是 IP 协议，还包括其他的网际协议和路由选择协议；也将网络层成为 IP 层；
- 链路层将分组有一个节点（主机或者路由器）传输到另一个，如以太网、WiFi 和电缆接入的 DOCSIS 协议，链路层的分组成为帧（frame）
- 物理层的作用是将帧中的一个个比特从一个端系统运输到另一个系统，物理层协议仍然使用链路层协议，与物理传输介质有关，双绞线、同轴电缆、光纤等；
  
- OSI 的七层模型，增加了表示层和会话层；表示层主要包括数据压缩和数据加密和数据描述，数据描述使得应用程序不必担心计算机内部存储格式的问题；会话层提供了数据交换的定界和同步功能，包括建立检查点和恢复方案；

- 一个 URL 到页面的步骤，首先 DNS域名解析成 IP 地址，TCP 三次握手建立连接，后发送 HTTP 请求，服务器处理请求并返回 HTTP 报文，浏览器负责解析渲染页面，TCP 四次挥手断开连接；
    - TCP 三次握手：
        - ① 客户端发送一个带 SYN=1，Seq=X 的数据包到服务器端口 
        - ② 服务器返回一个带 SYN=1，ACK=X+1，Seq=Y 的响应包，告知客户端，服务器已经准备好 
        - ③ 客户端回传一个带 ACK=Y+1，Seq=Z 的数据包，代表客户端即将发送请求，请做好准备；防止已经失效的连接请求突然又传送到服务端，因而产生的错误；三次握手后开始发送 HTTP 请求；
    - TCP 四次挥手（客户端和服务端均可发起）：
        - ① 发起方发送一个带 Fin=1 Ack=Z Seq=X 的数据包到接收端，并进入 FINWAIT 状态，该状态下客户端只接收数据, 不再发送数据
        - ② 接收方发送一个带 Ack=X+1 Seq=Z 的剩余数据分段，确认收到客户端的 FIN 信息，标识同意断开连接，进入FINWAIT状态 
        - ③ 接收方发送一个带 Fin=1 Ack=X Seq=Y 请求关闭连接，并进入 LAST_ACK 状态，告知报文已经发送完，发送方也准备关闭吧
        - ④ 发起方发送一个带 Ack=Y Seq=X 进入等待 TIME_WAIT 状态，接收方收到会关闭连接，发起方等待一定时间未收到回复则正常关闭连接
    - 为什么是三次握手：两次握手，网络环境比较复杂的情况，客户端可能会连续发送多次请求，如果只设计成两次握手的情况，服务端只能一直接收请求，然后返回请求信息，也不知道客户端是否请求成功
    - 一些过期请求的话就会造成网络连接的混乱；包的顺序可能不一致，客户端发送 SYN 包后会本地记录 Seq，发送多个 SYN，则记录的是最新的 Seq，客户端通过对比如果 Seq 不一致会发送 RST 包并从新建立连接；四次握手冗余，浪费资源；
    - TCP是全双工的，即客户端在给服务器端发送信息的同时，服务器端也可以给客户端发送信息。而半双工的意思是A可以给B发，B也可以给A发，但是A在给B发的时候，B不能给A发，即不同时，为半双工。 单工为只能A给B发，B不能给A发； 或者是只能B给A发，不能A给B发；
  
- 滑动窗口（Sliding window）
  - TCP 中采用滑动窗口来进行传输控制，滑动窗口的大小意味着接收方还有多大的缓冲区可以用于接收数据
  - 发送方可以通过滑动窗口的大小来确定应该发送多少字节的数据。当滑动窗口为 0 时，发送方一般不能再发送数据报。滑动窗口是 TCP 中实现诸如 ACK 确认、流量控制、拥塞控制的承载结构
  
## 进程间通信方式(IPC)
- 管道（Pipe）：管道可用于具有亲缘关系进程间的通信，允许一个进程和另一个与它有共同祖先的进程之间进行通信。
- 命名管道（named pipe）：命名管道克服了管道没有名字的限制，因此，除具有管道所具有的功能外，它还允许无亲缘关系进程间的通信。命名管道在文件系统中有对应的文件名。命名管道通过命令mkfifo或系统调用mkfifo来创建。
- 信号（Signal）：信号是比较复杂的通信方式，用于通知接受进程有某种事件发生，除了用于进程间通信外，进程还可以发送信号给进程本身；linux除了支持Unix早期信号语义函数sigal外，还支持语义符合Posix.1标准的信号函数sigaction（实际上，该函数是基于BSD的，BSD为了实现可靠信号机制，又能够统一对外接口，用sigaction函数重新实现了signal函数）。
- 消息队列：消息队列是消息的链接表，包括Posix消息队列system V消息队列。有足够权限的进程可以向队列中添加消息，被赋予读权限的进程则可以读走队列中的消息。消息队列克服了信号承载信息量少，管道只能承载无格式字节流以及缓冲区大小受限等缺
- 共享内存：使得多个进程可以访问同一块内存空间，是最快的可用IPC形式。是针对其他通信机制运行效率较低而设计的。往往与其它通信机制，如信号量结合使用，来达到进程间的同步及互斥。
- 内存映射（mapped memory）：内存映射允许任何多个进程间通信，每一个使用该机制的进程通过把一个共享的文件映射到自己的进程地址空间来实现它。
- 信号量（semaphore）：主要作为进程间以及同一进程不同线程之间的同步手段。
- 套接口（Socket）：更为一般的进程间通信机制，可用于不同机器之间的进程间通信。起初是由Unix系统的BSD分支开发出来的，但现在一般可以移植到其它类Unix系统上：Linux和System V的变种都支持套接字。
## 线程间通信
- 互斥量 只有拥有互斥量的线程才能执行任务
- 信号量 是一个计数器
- 事件 事件机制允许一个线程在处理完任务后，主动唤醒另一个线程执行任务

# 算法
## 如何判断单链表有环
用双指针进行判断，一个slow指针，一个fast指针从头开始扫描链表。指针slow每次走一步，fast指针每次走两步，如果fast指针遇到NULL时退出，则不存在环。如果slow、fast指针最终相遇，则存在环

## 数组中出现次数超过一半的数字
最开始看这道题，想到的是使用排序算法，先排序一下，然后在统计，最后比较。我们这样是比较麻烦。所以我就想到了HashMap。用HashMap来存储，数字用来做key，统计出现的次数作为value，并同时比较出现次数最多的key

## 二叉树中和为某一值的路径
先从根节点开始，用目标整数减去这个根节点的值，就是以后路径要相加所得值。开始往下走，遇到一个节点，就执行相减操作，直到目标值为0并且到达了叶子节点，则符合条件，则退回到上一节点，去其他路径继续做相同的操作

## 两数之和
如果不考虑时间复杂度，我们可以直接使用暴力的方法来求解，我们遍历每个元素 x，并查找是否存在一个值与 target - x相等的目标元素。这样的时间复杂度为O（n2），空间复杂度为O（1）。有没有更好的方法来解决这个问题呢，我们可以使用哈希表来解决这个问题。在进行迭代并将元素插入到哈希表中的同时，我们还会回过头来检查哈希表中是否已经存在当前元素所对应的目标元素。如果它存在，那我们已经找到了对应解，并立即将其返回。这样时间复杂度就变为O（n），空间复杂度为O（n）

# REST 是一种架构风格，满足如下约束：
① 客户端/服务端架构提供了基本的分布式，客户端发起请求，服务端响应或者拒绝，出错返回错误信息，客户端处理异常；
② 无状态，通信中的状态有客户端负责维护，请求中包含了全部的必要信息；
③ 缓存，有重复的请求，只需要第一次返回真正的执行结果，其他请求都可以共用这个请求直接返回结果；
④ 统一接口，熟悉这个架构的同事可以直接明白接口的意义，并延续下去；
⑤ 分层，每一次负责一个单一的职责，通过上层对下层的依赖组成一个完整的系统，通常包含应用层、服务层、数据处理层，应用层返回 json 数据和业务逻辑，服务处提供账号、文件托管等服务，数据处理层提供数据的存储和访问；
- 符合 REST 规范约束原则，称为 RESTfll 架构；
- 前后端解耦，减少服务器压力，前后端分工明确，提高安全性、稳定性；采用 HTTP 协议；
## 使用 django rest framework 框架的好处
能自动生成符合 RESTful 规范的 API
1.在开发REST API的视图中，虽然每个视图具体操作的数据不同，
但增、删、改、查的实现流程基本一样,这部分的代码可以简写
2.在序列化与反序列化时，虽然操作的数据不同，但是执行的过程却相似,这部分的代码也可以简写
REST framework可以帮助简化上述两部分的代码编写，大大提高REST API的开发速度

## django rest framework框架中的视图都可以继承哪些类
class View(object):
class APIView(View): 封装了view,并且重新封装了request,初始化了各种组件
class GenericAPIView(views.APIView):

## drf 提供的组件
序列化组件 serializers，对 QuerSet 序列化及对请求数据格式校验；

视图组件，帮助开发者提供了一些类，并在类中提供了多个方法；

渲染器，定义数据如何渲染到页面上，在渲染器 renderer_classes 中注册；

解析器，选择对数据解析的类，在解析器类 parser_classes 中注册；
分页，对数据进行分页处理 pagination_class；路由组件，由 routers 进行路由分发；

认证组件，注册到认证类 authentication_classes 类，在类的 authticate 方法中添加验证逻辑；

权限组件，注册到权限类 permission_classes 类，在 has_permission 方法中填写逻辑；

频率控制，注册到 throttle_classes 类，在 allow_request/wait 方法中添加逻辑；

版本控制，对来着不同客户端的请求使用不同的行为；

# django 
## ORM 管理器对象
每个继承自 models.Model 的模型类，都会有一个 objects 对象被同时继承下来，这个对象就叫做“管理器对象”，数据库的增删改查可以用 objects 管理器对象来实现
## Meta 内部类
Meta 定义的元数据相当于 Model 的配置信息
每个模型类（Model）下都有一个子类 Meta，这个子类就是定义元数据的地方
Django 会将 Meta 中的元数据信息附加到 Model 中。常见的元数据定义有 db_table（数据表名称）、abstract（抽象类） 、ordering（字段排序） 等，Meta 作为内部类，它定义的元数据可以让admin 管理后台对人类更加友好，数据的可读性更高。
元数据，即不属于 Model 的字段，但是可以用来标识字段一些属性

db_table 数据库表名称
abstract 是否是一个抽象类，不会对应数据库的表，用它来归纳一些公共属性字段
ordering 用于执行获取对象列表时的排序规则,默认升序,-是降序，？是随机
app_lable 模型不在默认的应用程序包下的 models.py 文件中，即指定模型属于那个app
indexs 一个列表类型的元数据项，用来定义 Model 的索引
default_permissions 默认会给每一个定义的 Model 设置三个权限即添加、更改、删除，它使用格式：default_permissions=('add','change','delete','view')
constraints 将约束添加到模型

## CSRF实现机制，跨站点请求伪造（Cross-site request forgery）
浏览器从一个域名的网页去请求另一个域名的资源时,浏览器出于安全的考虑，即满足同源策略：协议相同、域名相同、端口相同
Django 原生支持一个简单易用的跨站请求伪造的防护。当提交一个启用CSRF 防护的 POST 表单时，你必须使用上面例子中的csrf_token 模板标签。
第一步：django 第一次响应来自某个客户端的请求时,后端随机产生一个 token 值，把这个 token 保存在 SESSION 上下文状态中; 同时, 后端把这个 token 放到 cookie 中交给前端页面；
第二步：下次前端需要发起请求（比如发帖）的时候把这个 token 值加入到请求数据或者头信息中,一起传给后端；Cookies:{csrftoken:xxxxx}
第三步：后端校验前端请求带过来的 token 和 SESSION 里的 token 是否一致；

## 如何给CBV的程序添加装饰器
类中的方法与独立的函数不同，不能直接使用，可以通过 Django 中提供的 method_decorator 装饰器将函数装饰器转换为方法的装饰器; 也可以在类中实现 dispatch 方法，请求过来会先执行 dispatch 方法；
```
from django.utils.decorators import method_decorator

# method 1
@method_decorator(check_login, name="get")
class MyClass(View):
    def get(self, request):
        return render(request, "index.html)

# method 2
class MyClass(View):
    @method_decorator(check_login, name="get")
    def dispatch(self, request, *args, **kw):
        return super(MyClass, self).dispatch(request, *args, **kw)
    def get(self, request):
        return render(request, "index.html)

# method 3
class MyClass(View):
    def dispatch(self, request, *args, **kw):
        return super(MyClass, self).dispatch(request, *args, **kw)
    def get(self, request):
        return render(request, "index.html)
    @method_decorator(check_login)
    def post(self, request):
        return redirect("/index/")
```

## django请求的生命周期
(1.wsgi, 请求封装后交给 web 框架 （Flask、Django）
(2.中间件，对请求进行校验或在请求对象中添加其他相关数据，例如：csrf、request.session
(3.路由匹配 根据浏览器发送的不同 url 去匹配不同的视图函数
(4.视图函数，在视图函数中进行业务逻辑的处理，可能涉及到：orm、templates => 渲染 
(5.中间件，对响应的数据进行处理
(6.wsgi, 将响应的内容发送给浏览器

### django 请求的生命周期
一个 HTTP 请求，首先被 uWSGI 转化成一个 HttpRequest 对象，然后该对象被传递给Request 中间件处理，如果该中间件返回了 Response，则直接传递给 Response 中间件做收尾处理，
否则的话 Request 中间件将访问 URL 配置，确定哪个 view 来处理，在确定了哪个 view 要执行，但是还没有执行该 view 的时候，系统会把 request 传递给 view 中间件处理器进行处理，
如果该中间件返回了 Response，那么该 Response 直接被传递给 Response 中间件进行后续处理，否则将执行确定的 view 函数处理并返回 Response，
在这个过程中如果引发了异常并抛出，会被 Exception 中间件处理器进行处理;

## MIDDLEWARES中间件的作用和应用场景
中间件是介于 request 与 response 处理之间的一道处理过程,用于在全局范围内改变 Django 的输入和输出。
简单的来说中间件是帮助我们在视图函数执行之前和执行之后都可以做一些额外的操作
例如：
(1.Django 项目中默认启用了 csrf 保护,每次请求时通过 CSRF 中间件检查请求中是否有正确的 token 值
(2.当用户在页面上发送请求时，通过自定义的认证中间件，判断用户是否已经登陆，未登陆就去登陆。
(3.当有用户请求过来时，判断用户是否在白名单或者在黑名单里
```
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
```
## 列举 django 中间件的5个方法
process_request : 请求进来时,权限认证
process_view : 路由匹配之后,能够得到视图函数
process_exception : 异常时执行
process_template_response : 模板渲染时执行
process_response : 请求有响应时执行
- 可以新增自定义中间件统计接口耗时，自定义的权限验证等
## 列举 flask 中常用钩子函数
before_first_request 只有在处理第一次请求之前执行
before_request 在视图函数执行之前执行的钩子函数
context_processor 使用这个钩子函数，必须返回一个字典，这个字典中的值在所有模版中都可以使用
errorhandler 在发生一些异常的时候执行处理
after_request 必须传入一个参数来接收响应对象，并在最后return 这个参数，也就是返回响应内容

## only 和defer 的区别
only:从数据库中只取指定字段的内容
defer：指定字段的内容不被检索

## select_related 和 prefetch_related 的区别
有外键存在时，可以很好的减少数据库请求的次数,提高性能
select_related 通过多表 join 关联查询,一次性获得所有数据,只执行一次 SQL 查询
prefetch_related 分别查询每个表,然后根据它们之间的关系进行处理,执行两次查询

## filter和exclude的区别
取到的值都是 QuerySet 对象, filter 选择满足条件的, exclude 排除满足条件的

## F 和 Q 的作用
F: 对数据本身的不同字段进行操作 如:比较和更新
Q：用于构造复杂的查询条件 如：& |操作

## values 和 values_list 的区别
```
print(Question.objects.values('title'))   # 得到的是一个字典
<QuestionQuerySet [{'title': '查询优化之select_related与prefetch_related - 简书'}, {'title': '你们都是怎么学 Python 的？'}]>

print(Question.objects.values_list('title'))  # 等到是一个元组
<QuestionQuerySet [('查询优化之select_related与prefetch_related - 简书',), ('你们都是怎么学 Python 的？',)]>

print(Question.objects.values_list('title', flat=True))  # 得到的是一个列表
<QuestionQuerySet ['查询优化之select_related与prefetch_related - 简书', '你们都是怎么学 Python 的？']>
```

## union 与 union all
Union：对两个结果集进行并集操作，不包括重复行，同时进行默认规则的排序（默认按照主键升序）
Union All：对两个结果集进行并集操作，包括重复行，不进行排序

## 路由后面有没有 /
path("book", views.BookView.as_view())
如果定义路由的时候，没有/，则django会发送一个重定向的请求，这个请求是get
Django项目在settings.py文件中 默认使用UTC时间，而UTC时间（格林威治时间）比北京时间晚8小时
一般我们会把settings中的TIME_ZONE属性值改为 Asia/Shanghai， USE_TZ = False，LANGUAGE_CODE = 'zh-hans'
A.xxx  如果类中定义了 xxx则能找到，否则回去 __getattr__ 找

# Django DRF
下面重点对比了django.views.View 与 rest_framework.views.APIView，后者继承并扩展了前者的as_view与dispatch
```
from django.http.response import HttpResponse
class BookView(View) 或 (APIView):
    def get(self, request):
        return HttpResponse("get")
    def post(self, request):
        return HttpResponse("post")
    def delete(self, request):
        return HttpResponse("delete")

from django.views import View
class View:
    def dispatch(self, request, *args, **kwargs):
        handler = getattr(self, request.method.lower())
        return handler(request, *args, **kwargs)
    @classmethod
    def as_view(cls, **initkwargs):
        def view(request, *args, **kwargs):
            self = cls(**initkwargs)
            return self.dispatch(request, *args, **kwargs)
        return view

# from rest_framework.views import APIView
class APIView:
    def as_view(cls):
        view = super().as_view()
        # asyncio.iscoroutinefunction(func) 高版本有对异步协程的判断和处理
        return view
    def dispatch(self, request, *args, **kwargs):
        # 构建新的request对象
        request = self.initialize_request(request, *args, **kwargs)
        # 可以用request.data返回解析之后的请求数据；request._request返回django原生的request对象
        self.request = request
        # 初始化：认证、授权、限流组件
        self.initial(request, *args, **kwargs)
        # 分发逻辑不变
        handler = getattr(self, request.method.lower())
        return handler(request, *args, **kwargs)
```
## DRF (pip install djangorestframework)

from rest_framework.serializers import Serializer

```
path("sers/book/", views.BookView.as_view())

from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.views import APIView

from sers.models import Book

class BookSerializers(serializers.Serializer):
    title = serializers.CharField(max_length=32)  # 长度校验
    price = serializers.IntegerField(required=False) # required=False，即 可以没有
    pub_date = serializers.DateField()

    def create(self, validated_data):
        books = Book.objects.create(**validated_data)
        return books

    def update(self, instance, validated_data):
        Book.objects.filter(pk=instance.pk).update(**validated_data)
        updated_book = Book.objects.get(pk=instance.pk)
        return updated_book

class BookView(APIView):
    def get(self, request):
        book_lst = Book.objects.all()
        # 构建序列化对象, QuerySet -> Serializer -> .data (json)
        serializer = BookSerializers(instance=book_lst, many=True)
        return Response(serializer.data)

    def post(self, request):
        # 构建反序列化对象 json -> Serializers -> obj
        serializer = BookSerializers(data=request.data)
        if serializer.is_valid(): # 校验规则就是 BookSerializers 规定的格式CharFiled/max_length
            # 方式1，将保存数据库放在这里
            # books = Book.objects.create(**serializer.validated_data)
            # 方式二, 用序列化器的save方法，并在序列化器中实现create等其他方法, save 方法内部 会去调用序列化器的 create，这里是post，如果是put方法调用的是update
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer.errors)

# re_path("sers/book/{\d+}/", views.BookDetailView.as_view())
# 因为put/get/delete，他们都需要有一个pk，所以单独写在了一个类里，并且路由也是独立的
class BookDetailView(APIView):
    def get(self, request, book_id):
        book = Book.objects.get(pk=book_id)
        serializers = BookSerializers(instance=book, many=False)
        return Response(serializers.data)  # serializers.data 会自动完成序列化 object -> json

    def put(self, request, book_id):
        book_id = Book.objects.get(pk=book_id)
        # 部分更新，构建序列化对象进行反序列化，instance和data都要传递
        serializers = BookSerializers(instance=book_id, data=request.data)
        if serializers.is_valid():
            # 方式一
            # Book.objects.filter(pk=book_id).update(**serializers.validated_data)
            # updated_book = Book.objects.get(pk=book_id)
            # serializers.instance = updated_book
            # 方式二
            serializers.save()
            return Response(serializers.data)
        else:
            return Response(serializers.errors)

    def delete(self, request, book_id):
        Book.objects.get(pk=book_id).delete()
        return Response()
```
from rest_framework.serializers import ModelSerializer

    A `ModelSerializer` is just a regular `Serializer`, except that:
    * A set of default fields are automatically populated.
    * A set of default validators are automatically populated.
    * Default `.create()` and `.update()` implementations are provided.
    * 
即更加model表自动完成序列化组件创建，自动完成了create、update，也考虑了一对多、多对多
缺点是，模型组序列化组件将关联，耦合性比较高

```
from django.http import HttpResponse
from rest_framework import serializers
from rest_framework.generics import GenericAPIView

from sers.models import Book

class BookSerializers(serializers.ModelSerializer):
    date = serializers.DateField(source="pub_date")  # 也可灵活添加自定义的字段

    class Meta:
        model = Book
        fields = ["title", "price"]  # 默认 fields = "__all__"
        # exclude = ["pub_date"]

class BookView(GenericAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializers

    # def get(self, request):
    #   serializer = BookSerializers(instance=self.get_queryset(), many=True)
    #   serializer = self.get_serializer_class()(instance=self.get_queryset(), many=True)
    #   serializer = self.get_serializer(instance=self.get_queryset(), many=True)
    #   return HttpResponse(serializer.date)

    def get(self, request, pk):
        serializer = self.get_serializer(instance=self.get_object(), many=True)
        return HttpResponse(serializer.date)

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            pass
```
使用Mixin继续，简化增删改查查
```
from rest_framework.generics import GenericAPIView
from rest_framework.mixins import ListModelMixin, CreateModelMixin, \
    UpdateModelMixin, RetrieveModelMixin, DestroyModelMixin

class BookView(ListModelMixin, CreateModelMixin, GenericAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializers

    def get(self, request):
        return self.list(request)

    def post(self, request):
        return self.create(request)


class BookDetailView(RetrieveModelMixin, UpdateModelMixin, DestroyModelMixin, GenericAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializers
    
    def get(self, request, pk):
        return self.retrieve(request, pk)
    
    def put(self, request, pk):
        return self.update(request, pk)
    
    def delete(self, request, pk):
        return self.destroy(request, pk)
```
还可以继续简化
```
from rest_framework.generics import ListCreateAPIView
from rest_framework.generics import RetrieveUpdateDestroyAPIView

class BookView(ListCreateAPIView, GenericAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializers

class BookDetailView(RetrieveUpdateDestroyAPIView, GenericAPIView):
    queryset = Book.objects.all()
    serializer_class = BookSerializers
```
通过ViewSet解决类变量数据重复， 将增删改查查五个方法写到一起，需要改动分发机制，分发机制是APIView决定的，即重新指定分发
```
from rest_framework.viewsets import ViewSet  # 通过反射，在as_view内部，重新指定get的处理函数

    path("sers/book/", 
         views.BookView.as_view({"get": "get_all", "post": "add_object"}))
    re_path("sers/book/(?P<pk>\d+)",
            views.BookView.as_view({"get": "get_object", "delete": "delete_object", "put": "put_object"}))

class BookView(ViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializers

    def get_all(self, request):
        return Response("查看所有资源")
    def add_object(self, request):
        return Response("添加资源")
    def get_object(self, request, pk):
        return Response("查看单一资源")
    def update_object(self, request, pk):
        return Response("更新单一资源")
    def delete_object(self, request, pk):
        return Response("删除单一资源")
```

```
from rest_framework.viewsets import ModelViewSet
from rest_framework import serializers

 # 第一步，在路由上面进程处理
path("sers/book/",
    views.BookView.as_view({"get": "list", "post": "create"}))  # 这里指定的list和create处理函数，是ListModelMixin、CreateModelMixin提供的
re_path("sers/book/(?P<pk>\d+)",
    views.BookView.as_view({"get": "retrive", "delete": "destroy", "put": "update"})) # 同理，Retrieve/Update/Destroy

# 第二部，自定义序列化器
class BookSerializers(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ["title", "price"]

# 第三部，自定义View处理
class BookView(ModelViewSet): # ModelViewSet 继承了多个类，进一步进行了封装 
    queryset = Book.objects.all()
    serializer_class = BookSerializers
```
APIView 验证、权限、限流， 也可以自己扩展
```
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework.views import APIView

class ExampleView(APIView):
    # 类属性
    authentication_classes = [SessionAuthentication, BasicAuthentication]  # 认证，也可以在settings中定义全局的认证
    def get(self,request):
        pass 
class CustomAuthentication(BaseAuthentication): # 自定义认证方式
    def authenticate(self, request): #认证方法
        user = request.query_params.get("user")
        pwd  = request.query_params.get("pwd")
        if user != "root" or pwd != "houmen":
            return None
        # get_user_model获取当前系统中用户表对应的用户模型类
        user = get_user_model().objects.first()
        return (user, None)  # 按照固定的返回格式填写 （用户模型对象, None）
```
权限
```
'DEFAULT_PERMISSION_CLASSES': (
   'rest_framework.permissions.AllowAny',
    # AllowAny 允许所有用户，默认权限
    # IsAuthenticated 仅通过登录认证的用户
    # IsAdminUser 仅管理员用户
    # IsAuthenticatedOrReadOnly 已经登陆认证的用户可以对数据进行增删改操作，没有登陆认证的只能查看数据
)

from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

class ExampleView(APIView):
    permission_classes = (IsAuthenticated,)
    ...

from rest_framework.permissions import BasePermission
class IsXiaoMingPermission(BasePermission): # 自定义权限，可用于全局配置，也可以用于局部
# 如需自定义权限，需继承rest_framework.permissions.BasePermission父类，并实现以下两个任何一个方法或全部
    def has_permission(self, request, view):
        """
        视图权限，是否可以访问视图 view
        返回结果未True则表示允许访问视图类
        request: 本次客户端提交的请求对象
        view: 本次客户端访问的视图类
        """
        role = request.query_params.get("role")
        return role == "xiaoming"

    def has_object_permission(self, request, view, obj):
        """
        模型权限，是否可以访问模型对象 obj
        返回结果为True则表示允许操作模型对象
        """
        return True
```
限流
```
REST_FRAMEWORK = {
    # 限流全局配置
    'DEFAULT_THROTTLE_CLASSES':[ # 限流配置类
    #     'rest_framework.throttling.AnonRateThrottle', # 未认证用户[未登录用户]
    #     'rest_framework.throttling.UserRateThrottle', # 已认证用户[已登录用户]
        'rest_framework.throttling.ScopedRateThrottle', # 自定义限流
    ],
    # DEFAULT_THROTTLE_RATES 可以使用 second, minute, hour 或day来指明周期
    'DEFAULT_THROTTLE_RATES':{ # 频率配置
        'anon': '2/day',  # 针对游客的访问频率进行限制，实际上，drf只是识别首字母，但是为了提高代码的维护性，建议写完整单词
        'user': '5/day', # 针对会员的访问频率进行限制，
        'vip': '10/day', # 针对会员的访问频率进行限制，
    }
}

from rest_framework.throttling import UserRateThrottle
class Student2ModelViewSet(ModelViewSet):
    queryset = Student.objects
    serializer_class = StudentModelSerializer
    # 限流局部配置[这里需要配合在全局配置中的DEFAULT_THROTTLE_RATES来设置频率]
    # throttle_classes = [UserRateThrottle] # 使用drf限流类来配置频率
    throttle_scope = "vip" # 自定义频率
```
## 过滤
对于列表数据可能需要根据字段进行过滤，我们可以通过添加django-fitlter扩展来增强支持
pip install django-filter
```
INSTALLED_APPS = [
    ...
    'django_filters',  # 需要注册应用，
]

REST_FRAMEWORK = {
    ...
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',)
}
class StudentListView(ListAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentSerializer
    filter_fields = ['age', 'sex']
```
## 排序
对于列表数据，REST framework提供了OrderingFilter过滤器来帮助我们快速指明数据按照指定字段进行排序
在类视图中设置filter_backends，使用rest_framework.filters.OrderingFilter过滤器，REST framework会在请求的查询字符串参数中检查是否包含了ordering参数，如果包含了ordering参数，则按照ordering参数指明的排序字段对数据集进行排序
前端可以传递的ordering参数的可选字段值需要在ordering_fields中指明
```
from rest_framework.generics import ListAPIView
from students.models import Student
from .serializers import StudentModelSerializer
from django_filters.rest_framework import DjangoFilterBackend
class Student3ListView(ListAPIView):
    queryset = Student.objects.all()
    serializer_class = StudentModelSerializer
    filter_fields = ['age', 'sex']
    # 因为局部配置会覆盖全局配置,所以需要重新把过滤组件核心类再次声明,
    # 否则过滤功能会失效
    filter_backends = [OrderingFilter,DjangoFilterBackend]
    ordering_fields = ['id', 'age'] # -id 表示针对id字段进行倒序排序
```
## 分页 
django默认提供的分页器主要使用于前后端不分离的业务场景，所以REST framework也提供了分页的支持
```
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS':  'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100  # 每页数目
}
# 如果在配置settings.py文件中， 设置了全局分页，那么在drf中凡是调用了ListModelMixin的list()，都会自动分页。如果项目中出现大量需要分页的数据，只有少数部分的分页，则可以在少部分的视图类中关闭分页功能。
# 另外，视图类在使用过分页以后，务必在编写queryset属性时，模型.objects后面调用结果。例如：
# Student.objects.all()
class Student3ModelViewSet(ListAPIView):
    pagination_class = None

from  rest_framework.pagination import PageNumberPagination,LimitOffsetPagination
class StudentPageNumberPagination(PageNumberPagination):
    page_query_param = "page" # 查询字符串中代表页码的变量名
    page_size_query_param = "size" # 查询字符串中代表每一页数据的变量名
    page_size = 2 # 每一页的数据量
    max_page_size = 4 # 允许客户端通过查询字符串调整的最大单页数据量
class StudentLimitOffsetPagination(LimitOffsetPagination):
    limit_query_param = "limit" # 查询字符串中代表每一页数据的变量名
    offset_query_param = "offset" # 查询字符串中代表页码的变量名
    default_limit = 2 # 每一页的数据量
    max_limit = 4 # 允许客户端通过查询字符串调整的最大单页数据量

from .paginations import StudentPageNumberPagination,StudentLimitOffsetPagination
class Student3ModelViewSet(ModelViewSet):
    queryset = Student.objects.all()
    serializer_class = StudentModelSerializer
    # 取消当前视图类的分页效果
    # pagination_class = None
    # 局部分页
    pagination_class = StudentPageNumberPagination # StudentLimitOffsetPagination
```
## 异常处理 
REST framework提供了异常处理，我们可以自定义异常处理函数。例如我们想在要创建一个自定义异常函数
```
REST_FRAMEWORK = {
    'EXCEPTION_HANDLER': 'drfdemo.exceptions.custom_excetion_handle'
    # 如果未声明，会采用默认的方式，如下
    # 'EXCEPTION_HANDLER': 'rest_framework.views.exception_handler'
}

from rest_framework.views import exception_handler

def custom_exception_handler(exc, context):
    """
    自定义异常函数，必须要在配置文件中注册才能被drf使用
    exc: 异常对象，本次发生的异常对象
    context: 字典，本次发生异常时，python解析器提供的执行上下文
    所谓的执行上下文[context]，就是程序执行到当前一行代码时，能提供给开发者调用的环境信息异常发生时，代码所在的路径，时间，视图，客户端http请求等等...]
    """

    # 先调用REST framework默认的异常处理方法获得标准错误响应对象，在这个基础上增加更多处理即可
    response = exception_handler(exc, context)

    # 在此处补充自定义的异常处理
    if response is None:
        # 异常发生时的视图对象
        view = context['view']
        # 异常发生时的http请求
        request = context["request"]

        if isinstance(exc, DatabaseError):
            print('[%s]: %s' % (view, exc))
            response = Response({'detail': '服务器内部错误'}, status=status.HTTP_507_INSUFFICIENT_STORAGE)

        if isinstance(exc, TypeError):
            print("0不能作为除数~")
            print(request)
            response = Response({'detail': '0不能作为除数'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return response
```
## 自动生成接口文档
pip install coreapi
```
REST_FRAMEWORK = {
    # 。。。 其他选项
    # 接口文档
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.AutoSchema',
}

from rest_framework.documentation import include_docs_urls

urlpatterns = [
    ...
    path('docs/', include_docs_urls(title='站点页面标题')) # 设置接口文档访问路径
]
```

# Django makemigrations 和 migrate
makemigrations会把我们写的model生成数据库迁移文件
如果model中的meta添加了，managed=False，则不会对该model生成迁移代码
如果发生冲突，可以使用 makemigrations --merge 进行解决
migrate 将迁移文件集同步到数据库中
django_migrations 表会记录每次的migrate
当先对数据库中的字段进行了删除，但是没有删除model中的字段，此时migrate会报错，可以使用migrate --fake 来进行修复
如果数据库表已经存在，migrate建表操作的迁移可以通过migrate --fake-initial进行跳过
inspectdb 反向迁移，会检查setting中配置的数据库，将数据库表生成对应的model代码并打印出来

# JWT（JSON Web Token）
是一种在各方之间传输 JSON 对象作为信息的形式
授权
信息交换
JWT 将信息分为三个部分 header.payload.signature
    第一部分我们称它为头部（header):公司信息，加密方式
    第二部分我们称其为载荷（payload)：当前登录用户的信息：id，name，过期时间
    第三部分是签证（signature)：把前两段通过加密得到的串
## 签发和认证
- 用户携带用户名密码登录 -> 用户名密码是正确的 -> 签发token，返回给前端
- 用户访问需要登录后才能访问的接口，携带token过来，认证过后，才能允许访问
  即自定义类继承BaseAuthentication，实现authenticate，内部完成token的解析校验
```
class LoginView(APIView):
    def post(self, request):
        response = {'code': 101, 'msg': '用户名或密码错误'}
        username = request.data.get('username')
        password = request.data.get('password')
        user = User.objects.filter(username=username, password=password).first()
        if user:
            # 登录成功，签发token,通过当前登录用户获取荷载（payload）
            payload = jwt_payload_handler(user) # 配置中进行的实现
            # 通过payload生成token串（三段：头，payload，签名）
            token = jwt_encode_handler(payload)

            response['code'] = 100
            response['msg'] = '登录成功'
            response['token'] = token

        return Response(response)


from .auth import JwtAuthentication
class TestView(APIView):
    authentication_classes = [JwtAuthentication, ] # 自己写的认证类

    def get(self, request):
        print(request.user) # 这就是当前登录用户
        return Response('你必须登录，才能看到我')

# 全局使用，在配置文件中配置
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES':['app01.auth.JwtAuthentication'], # 全局生效

}
# 全局使用后，局部禁用
class LoginView(APIView):
    authentication_classes = []
```

# 面向对象特性：封装、继承、多态
- 封装是类和对象的主要特征，把客观事物封装成抽象的类，并且类可以将自己的数据和方法只让可信得类或对象操作，对不可信的进行隐藏
- 继承可以实现现有类的所有功能，并在无需重新变形原来类的情况下对这些功能进行扩展，继承创建的类称为子类或者派生类，被继承的类称为基类、父类或超类；简化了代码，减少了冗余；简化了对事物的认识和描述，清晰的体现类之间的层次关系，提供代码的健壮性和安全性；
- 多态是子类重写父类的方法，使子类具有不同的方法实现；将父类或者子类对象作为参数，运行时根据实际创建的对象类型动态决定使用哪个方法；

# RPC 、 微服务
远程过程调用计算机通信协议，允许进程间通信，屏蔽了底层的传输方式 TCP/UCP 、序列化和反序列化 XML/JSON/二进制 等内容只需要知道调用者的地址和接口就可以；主流框架有 Thrift、gRPC 等；
- RESTful API，每一次添加接口都需要额外的组织接口数据；其在应用层使用 HTTP 协议，相比较 RPC 一般使用二进制进行编码，数据量、流量消耗更大；RPC 就像本地方法调用；
- 对接外部时，使用 HTTP/RESTfull 等共有协议，对接内部的服务调用，选择性能更高的二进制私有协议；
- 微服务是一种架构模式，提倡将应用分解为非常小的、原子的微服务，特别是在云服务、移动互联网等技术的快速发展，并被大量使用；
    - 好处，是每个微服务专注于实现一个特定的功能，界限明确；微服务可以独立开发、持续集成和部署，发布周期更短；可是使用不同的开发语言；没有历史包袱，更容易采取最新的技术；
    - 缺点，增加了运维成本，需要更多的配置、部署、扩展和监控；如果微服务多了，管理整个系统也会比较麻烦；集成测试、上线需要花费更多的时间；
- Thrift，①第一步需要实现 .thrift 的 IDL 文件，struct 关键字将相关属性组合到一个结构体，定义返回字段和类型，exception 定义异常处理，service 中定义接口服务；② --gen 生成服务代码 ③ 定义 client.py 和 server.py 

# 乐观锁、悲观锁
- 悲观锁：总是假设最坏的情况，每次去拿数据的时候都认为别人会修改，所以每次在拿数据的时候都会上锁，这样别人想拿这
  个数据就会阻塞直到它拿到锁（共享资源每次只给一个线程使用，其它线程阻塞，用完后再把资源转让给其它线程）
- 传统的关系型数据库里边就用到了很多这种锁机制，比如行锁，表锁等，读锁，写锁等，都是在做操作之前先上锁
  - mysql 表锁：select * from tb for update
  - mysql 行锁：select id,name from tb where id=2 for update
  - 数据库约束：主键约束、唯一约束、默认值约束、非空约束、外键约束
  - 事务特性：原子性、一致性、隔离性、持久性
- 乐观锁：总是假设最好的情况，每次去拿数据的时候都认为别人不会修改，所以不会上锁，但是在更新的时候会判断
  一下在此期间别人有没有去更新这个数据，可以使用版本号机制和CAS算法实现。乐观锁适用于多读的应用类型，这样
  可以提高吞吐量，像数据库提供的类似于 write_condition 机制，其实都是提供的乐观锁
    - 版本号机制：一般是在数据表中加上一个数据版本号 version 字段，表示数据被修改的次数，当数据被修改时，version值会加一。当线程A要更新数据值时，在读取数据的同时也会读取version值，在提交更新时，若刚才读取到的version值为当前数据库中的version值相等时才更新，否则重试更新操作，直到更新成功
    - CAS机制，compare and swap，需要读写的内存值 V，进行比较的值 A，拟写入的值 B，当且仅当 V 与 A 相等是，通过原子操作用 B 更新 V，否则不会执行任何操作

# 二叉树中序遍历，按层次遍历，树的深度
```
class BinTree:
    def __init__(self, data):
        self.data = data
        self.left = None
        self.right = None
def in_order(root):
    if root:
        in_order(root.left)
        print(root.data)
        in_order(root.right)
def level_order(root):
    from collection import deque
    q = deque()
    if root:
        q.append(root)
    while len(q) > 0:
        node = q.popleft()
        print(node.data)
        if node.left:
            q.append(node.left)
        if node.right:
            q.append(node.right)
def maxDepth(root):
    if not root:
        return 0
    return max(maxDepth(root.left), maxDepth(root.right)) + 1
```

# 链表逆置
```
class Node:
    def __init__(self, data):
        self.data = data
        self.next = None
def rever_list(head):
    cur = head
    pre = None  # 头结点的上一个结点是空
    while cur:
        next = cur.next  # 当前结点的下一个结点
        cur.next = pre
        pre = cur  # 前进一步
        cur = next # 前进一步
    return pre
```

# 判断101-200之间有多少个质数
```
b = 0
for a in range(101, 201):
    k = 0
    for i in range(2, a):
        if a % i == 0:
            k += 1
            break
    if k == 0:
        b += 1
print(b)
```

# 斐波那锲数列
```
def  fib(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return b
def d(func):
    cache = {}
    def wrapper(*args):
        if args not in cache:
            cache[args] = func(*args)
        return cache[args]
    return wrapper
@d
def fib(n):
    if n < 2:
        return 1
    return fib(n-1) + fib(n-2)
```

# 两个链表求交叉点
链表 A 总长 a，公共长度 c，先遍历 A，再遍历 B，则到公共节点时，共走过了 a + (b - c)
链表 B 总长 b，公共长度 c，先遍历 B，再遍历 A，则到公共节点时，共走过了 b + (a - c)
公共节点满足：a + (b - c) = b + (a - c)
```
class ListNode:
    def __init__(self, x):
        self.val = x
        self.next = None
class Solution:
    def getIntersectionNode(self, headA: ListNode, headB: ListNode) -> ListNode:
        A, B = headA, headB
        while A != B:
            A = A.next if A else headB
            B = B.next if B else headA
        return A
```

# 清除 json 里面的空数据，包括空dict、空list、空string 和 None
```
def value_is_not_empty(value):
    return value not in ['', [], {}, None]

def empty_json_data(data):
    if isinstance(data, dict):
        out = dict()
        for k, v in data.items():
            if value_is_not_empty(v):
                sub = empty_json_data(v)
                if value_is_not_empty(sub):
                    out[k] = sub
        return None if not out else out
    elif isinstance(data, list):
        out = list()
        for value in data:
            if value_is_not_empty(value):
                new_value = empty_json_data(value)
                if value_is_not_empty(new_value):
                    out.append(new_value)
        return None if not out else out
    elif value_is_not_empty(data):
        return data

print(empty_json_data({"a": []}))
print(empty_json_data({"a": {"b": "b", "c": [], "d": {}}}))
print(empty_json_data({"a": {"a": [None, "", {}, {"x": None}]}, "b": 0}))
```

## 将 IP 地址转换为正数
```
def func(addr):
    # 取每个数, int, bin, ord, hex
    id = [int(x) for x in addr.split(".")]
    # 移动不同的位数，求和
    return sum(id[i] << [24, 16, 8, 0][i] for i in range(4))

def func_reverse(num):
    v1 = num >> 24
    v2 = (num - (v1 << 24)) >> 16
    v3 = (num - (v1 << 24) - (v2 << 16)) >> 8
    v4 = (num - (v1 << 24) - (v2 << 16) - (v3 << 8)) >> 0
    return "{}.{}.{}.{}".format(v1, v2, v3, v4)

addr = "127.0.0.1"
num = func(addr)
addr_ori = func_reverse(num)
print(addr, num, addr_ori)
```

## 打家劫舍问题
⼀棵⽵⼦有n个⽵节，每个⽵节上有不同数量的蚂蚁（可以⽤数组表示），现清理⽵节上的
蚂蚁，但不能清理相邻⽵节的蚂蚁，请通过编程计算最多能清理多少蚂蚁
```
def remove_ants(nums):
    n = len(nums)
    if n == 0:
        return 0
    if n == 1:
        return nums[0]
    ants = [0] * n
    ants[0], ants[1] = nums[0], max(nums[0], nums[1])
    for i in range(2, n):
        ants[i] = max(ants[i-1], ants[i-2] +nums[i])
    return ants[-1]  # 最后一个元素，即最多能清理多少蚂蚁
```

## 兔子繁殖问题
编程题：（不是斐波那契数列⽅式）起初⼀对兔⼦，每4个⽉成熟后⽣育下⼀对兔⼦（成熟后⼀
对兔⼦在接下来每⼀个⽉都会⽣育⼀对兔⼦），那么请问理想状态下，第10个⽉总共有多少对兔⼦，
如果是5个⽉才成熟，24个⽉后⼜是多少？同时可以思考是否有通⽤型算法；（tip:类和数组）（算
法 要满⾜ 1000 个⽉后不卡死）
```
month=int(input('繁殖几个月？： '))
month_1=1
month_2=0
month_3=0
month_elder=0
for i in range(month):
    month_1,month_2,month_3,month_elder=month_elder+month_3,month_1,month_2,month_elder+month_3
    print('第%d个月共'%(i+1),month_1+month_2+month_3+month_elder,'对兔子')
    print('其中1月兔：',month_1)
    print('其中2月兔：',month_2)
    print('其中3月兔：',month_3)
    print('其中成年兔：',month_elder)

class Rabbit:
    month = []  # 元素0表示1月兔子数，1表示2月兔子数
    count = 4   # or 5, 表示需要几个月会生育下一代
    cur = 1     # 初始是一对兔子
    mature = 0  # 成熟的兔子数，即count之后的兔子会变为成熟兔子

    def __init__(self):
        self.month = [0 for _ in range(self.count)]
        self.month[0] = self.cur

    def cur_rabbit(self, n):
        for i in range(n):
            self.mature = self.mature + self.month[self.count - 1]
            for i in list(range(self.count))[::-1]:
                self.month[i] = self.month[i-1]
            self.month[0] = self.mature + self.month[self.count - 1]
        print(n, self.month, self.mature, '合计兔子对数:', sum(self.month) + self.mature)
        # 合计兔子对数，即  sum(self.month) + self.mature

Rabbit().cur_rabbit(1)
Rabbit().cur_rabbit(2)
Rabbit().cur_rabbit(3)
Rabbit().cur_rabbit(4)
Rabbit().cur_rabbit(5)
```


# 判断输出值
a = "123"; b = a; 此时 a,b 指向同一个内存地址；b = b[:-1]; 此时 b 指向一个新的地址，最后：a="123", b="12"
b = [[]] * 2 值为 [[], []]; b[0]、b[1] 指向同一个内存地址 b[0].append(1); 此时 b = [[1], [1]]; 如果使用 b[0] = 1, 此时 b = [[1], []]
集合使用一堆内存来存储大量数据，in 运算是，集合比列表快，元组使用的内存比列表小，in 的速度几乎相同

作用域（java）  当前类  同包下  子孙下  其他包
public          √       √      √       √
protect         √       √      √
default         √       √
private         √
作用域（C++）
public    <可以被任意实体访问> 公有成员，无论类内还是类外（包括继承者）的函数都可以访问public成员
private   <只允许本类的成员函数访问> 私有成员，仅有类内函数可以访问 private，类外一切函数（包括继承者）均不可访问 
protected <只允许子类及本类的成员函数访问> 即保护成员，主要用在类的继承中，类内可访问，继承者中成员函数访问，而无法被类外任何函数访问
### 最大递归深度
避免堆栈溢出.Python解释器限制了递归的深度,以帮助您避免无限递归,从而导致堆栈溢出.
尝试增加递归限制(sys.setrecursionlimit)或重写代码而不递归
```
import sys
sys.getrecursionlimit() # 3000，不同的版本和系统不同
sys.setrecursionlimit(3000)

def recursiveFunction(n, sum):
    if n < 1:
        return sum
    else:
        return recursiveFunction(n-1, sum+n)
print(recursiveFunction(2982, 0))  # 实际测试最大是2982， 比3000小
```
## ascii、unicode、utf-8、gbk 区别
python2内容进行编码（默认ascii）,而python3对内容进行编码的默认为utf-8。
ascii   最多只能用8位来表示（一个字节），即：2**8 = 256，所以，ASCII码最多只能表示 256 个符号。
unicode  万国码，任何一个字符==两个字节
utf-8     万国码的升级版  一个中文字符==三个字节   英文是一个字节  欧洲的是 2个字节
gbk       国内版本  一个中文字符==2个字节   英文是一个字节
gbk 转 utf-8  需通过媒介 unicode

# 可变集合 set 与不可变集合 frozenset
set 无序且不重复，是可变的，有add（），remove（）等方法
基本功能包括关系测试和消除重复元素. 集合对象还支持union(联合), intersection(交集), difference(差集)和sysmmetric difference(对称差集)等数学运算

frozenset是冻结的集合，它是不可变的，存在哈希值，好处是它可以作为字典的key，也可以作为其它集合的元素。缺点是一旦创建便不能更改，没有add，remove方法

set()和 frozenset()工厂函数分别用来生成可变和不可变的集合。如果不提供任何参数，默认会生成空集合。如果提供一个参数，则该参数必须是可迭代的，即，一个序列，或迭代器，或支持迭代的一个对象，例如：一个列表或一个字典

集合间操作，如或 |， 与 ^， 差 - 等
如果左右两个类型相同，结果的类型也一样；如果左右类型不一致，结果与左边的类型一致

## filter 与 map 总结
参数：都是一个函数， 加一个可迭代对象，返回值是可迭代对象
filter 是做筛选的，结果还是原来就在可迭代对象中的项
map 是对可迭代对象中每一项做操作的，结果不一定是原来就在可迭代对象中的项
zip 拉链函数，将对象中对应的元素打包成一个个元组，返回一个迭代器，如果各个迭代器的元素个数不一致，则返回列表长度与最短的对象相同
reduce 函数会对参数序列中元素进行累积，对数据集中所有元素执行操作；py3 中移动到了 from functools import reduce 中

## isinstance \ type
isinstance() 函数来判断一个对象是否是一个已知的类型，类似 type()
type() 不会认为子类是一种父类类型，即不考虑继承关系
isinstance() 会认为子类是一种父类类型，考虑继承关系
如果要判断两个类型是否相同推荐使用 isinstance()

## re 的 match 和 search 区别
re.match 尝试从字符串的起始位置匹配一个模式，如果不是起始位置匹配成功的话，match()就返回 None
re.search 扫描整个字符串并返回第一个成功的匹配
正则的贪婪匹配: 匹配一个字符串没有限制，能匹配多少就去匹配多少，直到没有匹配的为止

## 1 or 2, 1 and 2
1 or 2, 结果是1
1 and 2，结果是2
python 中的and从左到右计算表达式，若所有值均为真，则返回最后一个值，若存在假，返回第一个假值

## def func(a,b=[]) 这种写法有什什么坑
```
def func(a,b = []):
    b.append(1)
    print(a,b)
func(2)
func(2)
func(2) # 输出结果是 2, [1, 1, 1]

def func(a,b = None):
    if not b:
        b = []
    b.append(1)
    print(a,b)
func(2)
func(2)
func(2) # 输出结果是 2, [1]

def f(x,l=[]):
    for i in range(x):
        l.append(i*i)
    print (l)
f(2)          # [0, 1]
f(3,[3,2,1])  # [3, 2, 1, 0, 1, 4]
f(3)          # [0, 1, 0, 1, 4]
```

## a = [1,2,3] 和 b = [(1),(2),(3) ] 以及 b = [(1,),(2,),(3,) ] 的区别
a, b 保存的内容一样的 [1, 2, 3]
c 中的元素则是 tuple

## 1、2、3、4、5 能组成多少个互不相同且无重复的三位数
```
import itertools
print(len(list(itertools.permutations('12345', 3))))  # 60
```

## 面向对象深度优先和广度优先是什么
Python的类可以继承多个类，Python的类如果继承了多个类，那么其寻找方法的方式有两种
当类是经典类时，多继承情况下，会按照深度优先方式查找  
当类是新式类时，多继承情况下，会按照广度优先方式查找  
简单点说就是：经典类是纵向查找，新式类是横向查找
经典类和新式类的区别就是，在声明类的时候，新式类需要加上object关键字。在python3中默认全是新式类
不管是不是显式地继承自object。所有的类都继承自object，不管显式隐式，所有对象都是object的实例，包括内置类型
上面说的就是 MRO： Method Resolution Order

# GIL 的功能是
GIL 不是 Python 的特点，而是 CPython 解释器的特点
在 CPython 解释器中，GIL 是一把互斥锁，用来阻止同一个进程下多个线程的同时执行
CPython 解释器的内存管理并不安全( 内存管理—垃圾回收机制)
在没有 GIL 锁的情况下，有可能多线程在执行一个代码的同时，垃圾回收机制线程对所执Python 是一门解释型的语言，这就意味着代码是解释一行，运行一行，它并不清楚代码全局
因此，每个线程在调用 cpython 解释器 在运行之前，需要先抢到 GIL 锁，然后才能运行
编译型的语言就不会存在 GIL 锁，编译型的语言会直接编译所有代码，就不会出现这种问题
```
import sys
a = []
print(sys.getrefcount(a))  # 2
b = a
print(sys.getrefcount(a))  # 3

```
CPython 引进 GIL，可以最大程度上规避类似内存管理这样复杂的竞争风险问题
GIL 也不能保证绝对的线程安全，多线程编程时还是要注意
```
import time
from threading import Thread,Lock


mutex = Lock()
number = 10

def func(mutex):
    mutex.acquire()
    global number
    tem = number
    time.sleep(0.1)
    number = tem -1
    mutex.release()

if __name__ == '__main__':

    thread_list = []
    for i in range(10):
        thread = Thread(target=func,args=(mutex,))
        thread.start()
        thread_list.append(thread)
    for i in thread_list:
        i.join()

    print(number)
```

# 在python中有一些与下划线相关的约定
单独一个下划线_也是一个变量，表示一个临时对象，一般后续不会用到
单下划线_也可以表示程序中运行的最近一个结果
单下划线_作为函数名时，一般是代表了国际化和本地化字符串之间翻译查找的函数
- 单下划线开头的变量
单下划线开头_var的变量或函数_fun表示该变量或函数为内部使用的变量，不建议在外部使用，但单下划线开头仅仅是一个提示，没有权限控制，实际上可以在外部访问。
同时，如果用from <module> import *和from <package> import *时，这些属性、方法、类将不被导入
单下划线结尾var_，为了防止跟系统关键字重名了，比如函数里需要有个参数class，但是Python中class为关键字，所以需要将 class设置为class_
- 双下划线开头的变量
  - 双下划线开头的变量是类里面的私有变量，只能在类的内部访问，在外部是不允许访问的和修改的,可以使用方法去间接的获取和修改
  - 用间接获取也能获取到，python只是把私有变量的名字给修改了 object._claseName.__varible, 即 _类名__变量
前后双下划线变量__var__或函数__fun__()，是系统定义的变量名称或函数，我们定义变量名称或函数是应该尽量避免前后加双下划线

# 事务隔离级别
事务隔离级别	                     脏读	不可重复读	幻读
读未提交（read-uncommitted）	       是	   是	    是
不可重复读/读已提交（read-committed）	否	    是       是
可重复读（repeatable-read）	           否	   否       是
串行化（serializable）	               否	   否       否
- 不可重复读的和幻读很容易混淆，不可重复读侧重于修改，幻读侧重于新增或删除
- 解决不可重复读的问题只需锁住满足条件的行，解决幻读需要锁表
-  mysql默认事务隔离级别是REPEATABLE-READ（可重复读），对同一字段的多次读取结果都是一致的，除非数据是被本身事务自己所修改，可以阻止脏读和不可重复读，但幻读仍有可能发生。
-  
## SQL标准定义了四个事务隔离级别:
- 1、READ-UNCOMMITTED（读取未提交）∶最低的隔离级别，允许读取尚未提交的数据变更，可能会导致脏读、幻读或不可重复读。
- 2、READ-COMMITTED（读取已提交）∶允许读取并发事务已经提交的数据，可以阻止脏读，但是幻读或不可重复读仍有可能发生。
- 3、REPEATABLE-READ（可重复读）∶对同一字段的多次读取结果都是一致的，除非数据是被本身事务自己所修改，可以阻止脏读和不可重复读，但幻读仍有可能发生。
- 4、SERIALIZABLE（可串行化）︰最高的隔离级别，完全服从ACID的隔离级别。所有的事务依次逐个执行，这样事务之间就完全不可能产生干扰，也就是说，该级别可以防止脏读、不可重复读以及幻读。

脏读：事务A读取了事务B更新的数据，然后B回滚操作，那么A读取到的数据是脏数据
不可重复读：事务 A 多次读取同一数据，事务 B 在事务A多次读取的过程中，对数据作了更新并提交，导致事务A多次读取同一数据时，结果 不一致。
幻读：管理员将表中所有数据进行统一修改，这时候插入一条新数据，管理员改完后发现有一条记录没改过来，就好像发生了幻觉一样，这就叫幻读。
不可重复读的和幻读很容易混淆，不可重复读侧重于修改，幻读侧重于新增或删除。解决不可重复读的问题只需锁住满足条件的行，解决幻读需要锁表


# EXPLAIN字段详解
- id： 的编号是 select 的序列化，比较简单的查询语句只有一个 select，复杂的查询如包含子查询或包含 union 语句的情况会有多个 select，有几个就有几行；
- select type：每个 select 的查询类型，有 SIMPLE 即简单 select，不使用 union 和子查询；PRIMARY 查询中包含了复杂的字部分；UNION 使用了 union 中第二个后面的 select 语句； UNION RESULT 即 union 的结果；SUBQUERY 即子查询的第一个 select；
- table：表示数据来自哪张表，可能是虚表；
- type：标识关联类型和访问类型，即如何查找表中的行，查询记录的大概范围；性能由好到差依次为：system>const>eq_ref>ref>range>index>all
    - system 只有一行
    - count 索引一次就可以找到
    - eq_ref 唯一性索引扫描，表中只有一条记录与之匹配，一般是两表关联，关联条件字段是表的主键或者唯一索引
    - ref 非惟一行索引扫描，返回匹配某个单独值得所有行
    - range 索引给定范围的行，一般查询条件中出现了 > 、<、in、between 等查询
    - index 遍历索引树，比 all 快，因为索引文件通常更新，是读全表；index 是从索引中检索，all是从硬盘中检索
    - all 遍历全表找到匹配的行
- possible_keys 可能使用到的索引，并不一定会用到
- key 实际使用的索引，如果没有使用索引是 NULL
- key_len 索引使用的字节数
- ref 在 key 列记录的索引中，表查找值所用到的列或者常量，常有 const、func、NULL、字段名
- rows 大致查询所要读取的行数
- filtered 选取的行和读取的行的百分比
- Extra 额外信息，Using where、Using filesort、Using temporary、Using index

# MYSQL 优化
- 慢查询排查；通过慢查询日志或者监控，找到比较慢的 SQL 语句，执行 explain 查询 SQL 语句的执行计划；type=all 则为全表扫描；key 实际使用的索引，没有就是 Null；rows 查询大致需要读取的行数
- 视图：视图是一个虚拟表，不是真实存在的（只能查，不能改）
- 覆盖索引，在索引表中就能将想要的数据查询到
- 水平分表：讲些历史信息分到另外一张表中，例如：支付宝账单，几个月前的数据查询肯定少
- 垂直分表：将某些列拆分到另外一张表，例如：博客+博客详情

- 优化 SQL 语句和索引 
① 正确使用索引；如果没有索引查询的时候会进行全表扫描，查询数据多、效率低，需要对经常使用的查询字段添加相应的索引；
  尽可能的使用主键查询，他不会触发回表，因此节省一部分时间；适当的使用前缀索引，索引越长占用的磁盘空间就越大，相同数据页可以存放的索引值也就越少，新增、删除数据时索引变动需要的时间也越长；
② 查询具体字段，而非全部字段，避免使用 select *
③ 优化子查询，尽量使用 join 来替代子查询，子查询会创建和销毁临时表会占用系统资源并花费一定的时间，而 join 不会创建临时表 
④ 注意查询顺序，使用小表驱动大表，优先查询数据量小的表
⑤ 不要在列上进行算数运算或其他表达式运算，可能导致不能命中索引
⑥ 正确使用联合索引，要满足最左匹配，如果联合索引已经包含则不要重复建立索引
⑦ in 中不要包含过多的值
⑧ 当只需要一条数据的时候，使用 limit 1
⑨ 使用分页 limit begin_index，offset
    - select SQL_CALC_FOUND_ROWS * from foods_info LIMIT 0,10;
    - SELECT FOUND_ROWS() as total;
    - 看起来是两条数据，但是实际上只进行了一次数据库查询
⑦ mysql 通过配置 slow_query_log=1 开启慢查询记录，会对 MYSQL 的性能有一定影响，生产环境要慎用；
- 联合索引abc，a,ab,ac,abc都会走索引；ab,ac,a会部分走索引，其他情况不走索引
- 查询ac，a可以命中索引，c无法命中索引，ac即部分走索引，possible_keys会显示用了联合索引，但实际并没有用联合索引，只是部分用了索引
- 最左匹配原则，mysql会一直向右匹配直到遇到范围查询（> < between like )就停止匹配，即后面的索引会失效
  
- 慢查询日志有没有开 show variables like '%slow_query_log%';
- 慢查询门槛值是 show variables like '%long_query_time%';
- log 的输出方式是TABLE，才能把结果记录在数据库表中 show variables like '%log_output%';
- 在slow_log表中，query_time是我们最关心的，select query_time, rows_sent, rows_examined, db from mysql.slow_log where query_time > 10 and rows_sent < 100 limit 10;
- 只取一条 select sql_text from mysql.slow_log order by start_time desc limit 1;
- show index from b;
- alter table b add index b_parent (parentid);
  
## Show Profile 分析 SQL 执行性能
select @@have_profiling 返回 YES 表示功能已开启
mysql> show profiles;
mysql> set profiling=1; # 开启
mysql> show profiles;
mysql> show profile for query ID ，查看 SQL 语句在执行过程中线程的每个状态所消耗的时间

## 使用limit offset 分页时，为什么越往后翻越慢
select * from table limit 0,10 扫描满足条件的10行，返回10行。
但当执行select * from table limit 800000，20 的时候数据读取就很慢，limit 800000，20的意思扫描满足条件的800020行，扔掉前面的800000行，返回最后的20行，可想而知这时会很慢，测试了一下达到37.44秒之久
- 利用覆盖索引 select id from product order by id limit 800000, 20
- 利用子查询 select * from product 
where ID >= ( select id from product order by id limit 800000,1 ) limit 20
- 利用 join，select * from product a
JOIN ( select id from product order by id limit 800000,20 ) b on a.id = b.id
- 子查询和关联查询性能对比
  - 子查询：把内层查询结果当作外层查询的比较条件，使用 IN( ) 函数、EXISTS 运算符等
  - 执行子查询时，MYSQL需要创建临时表，查询完毕后再删除这些临时表，所以，子查询的速度会受到一定的影响，这里多了一个创建和销毁临时表的过程
  - 连接查询（JOIN）连接查询不需要建立临时表，因此其速度比子查询快。另外注意：能过滤先过滤，过滤好了再链接
- 先定位到上一次分页的最大 id，然后对 id 做条件索引查询
  - select * from 表 where id > #{id}  limit  #{pageSize};
- 并且，减少select * 的使用，因为数据都存储在主键索引（聚簇索引）上，即可能产生回表操作，尽量将需要的字段列出，并且字段尽量在覆盖索引中，从而减少回表

## MyISAM 和 InnoDB 的区别
- InnoDB 支持事务，MyISAM 不支持
- InnoDB 支持外键，而 MyISAM 不支持
- InnoDB 是聚集索引，使用B+Tree作为索引结构，数据文件是和（主键）索引绑在一起的
- MyISAM 是非聚集索引，它也是使用B+Tree作为索引结构，但是索引和数据文件是分离的，索引保存的是数据文件的指针
- InnoDB 必须要有主键，MyISAM可以没有主键
- InnoDB 辅助索引和主键索引之间存在层级关系(需要回表)；MyISAM辅助索引和主键索引则是平级关系(聚集索引和非聚集索引叶子存的都是数据文件的地址)
- InnoDB 不保存表的具体行数，执行select count(*) from table时需要全表扫描。而MyISAM用一个变量保存了整个表的行数，执行上述语句时只需要读出该变量即可，速度很快（注意不能加有任何WHERE条件）
- Innodb 不支持全文索引（5.7之后开始支持），而MyISAM支持全文索引
- InnoDB 支持表级锁、行级锁，默认为行级锁；而 MyISAM 仅支持表级锁。InnoDB 的行锁是实现在索引上的，而不是锁在物理行上。如果访问未命中索引，也是无法使用行锁，将会退化为表锁
- innodb 2个文件.ifm（表结构） 、.ibd(数据和索引)， myisam 3个文件 .ifm（表结构） 、.myd(数据文件)、.myi（索引文件)
- select：myisam性能高（适合读多写少），update、insert：innodb性能高（适合写多读少）
- 清空整个表时，InnoDB是一行一行的删除，效率非常慢。MyISAM则会重建表


# 系统设计
订单进行实时的统计，包括实时的交易金额与交易订单量，不同支付方式总金额、订单量和占比，当天各个时间段的数据统计
- 交易成功后，向 Redis 中发布消息，并发送数据到 Redis 的 list 队列
- 监听服务负责 Redis 消息的订阅和进行统计，统计完成后，定时任务会来取结果
- 主进程会异步的方式，向 MongoDB 写入订单，做历史的统计
- MongoDB 创建并使用集合：use xxx；查看当前工作的集合： db；查看所有非空集合： show dbs；查看当前集合的所有数据：db.table.find()

# ES
## 倒排索引
索引：从ID到内容
倒排索引：从内容到ID；好处：比较适合做关键字检索，可以控制数据的总量，提高查询效率
标准分词器 standard 分词器提供基于语法的分词（基于 Unicode 文本分割算法）并且适用于大多数语言。
ik分词器，es中默认的分词器，都是支持英文的，中文需要安装自己的分词器

## ES 写入数据的工作步骤
1、客户端发写数据的请求时，可以发往任意节点。这个节点就会成为 coordinating node 协调节点
2、计算的点文档要写入的分片：计算时就采用hash取模的方式来计算
3、协调节点就会进行路由，将请求转发给对应的主副片 primary sharding所在的datanode
4、datanode节点上的primary sharding处理请求，写入数据到索引库，并且将数据同步到对应的副本片 replica sharding
5、等primary sharding 和 replica sharding都保存好文档了之后，返回客户端响应

## ES 查询数据的工作步骤
1、客户端发请求可发给任意节点，这个节点就成为协调节点
2、协调节点将查询请求广播到每一个数据节点，这些数据节点的分片就会处理改查询请求
3、每个分片进行数据查询，将符合条件的数据放在一个队列当中，并将这些数据的文档ID、节点信息、分片信息都返回给协调节点
4、由协调节点将所有的结果进行汇总，并排序
5、协调节点向包含这些文档ID的分片发送get请求，对应的分片将文档数据返回给协调节点，最后协调节点将数据整合返回给客户端。

# 范式，三大范式与反范式
范式是符合某一种级别的关系模式的集合，表示一个关系内部属性之间的联系合理化程度
粗略理解：就是一张数据表的表结构所符合的某种设计标准的级别
- 第一范式 1NF：数据库表的每一列是不可分割的（原子性），同一列不能有多个值
- 第二范式 2NF：在一的基础上，数据表里的所有数据都要和主键有完全依赖关系，如果只和主键有一部分关系，需要进行拆分
- 第三范式 3NF：在二的基础上，非主键属性只和主键有相关性，而非主键属性之间是独立无关的
- 反范式，是通过增加冗余或数据分组来优化数据读取性能的过程；某些情况下，反范式是解决数据库性能和伸缩性的极佳策略

# 深拷贝、浅拷贝
1.深拷贝，拷贝的程度深，自己新开辟了一块内存，将被拷贝内容全部拷贝过来了；
2.浅拷贝，拷贝的程度浅，只拷贝原数据的首地址，然后通过原数据的首地址，去获取内容。
两者的优缺点对比：
（1）深拷贝拷贝程度高，将原数据复制到新的内存空间中。改变拷贝后的内容不影响原数据内容。但是深拷贝耗时长，且占用内存空间。
（2）浅拷贝拷贝程度低，只复制原数据的地址。其实是将副本的地址指向原数据地址。修改副本内容，是通过当前地址指向原数据地址，去修改。所以修改副本内容会影响到原数据内容。但是浅拷贝耗时短，占用内存空间少
## 浅拷贝
- 有一层数据类型，且数据类型时可变数据类型，例如：列表、字典 import copy; a = [1, 2, 3]; b = copy.copy(a); id(a) 与 id(b) 不一致
- 有一层数据类型，且数据类型时不可变数据类型，例如：元组、字符串 import copy; a = (1, 2, 3);  b = copy.copy(a); id(a) 与 id(b) 一致
- 有两层数据类型，外层为可变数据类型，内层为可变数据类型
  - a, b = [1, 2], [3, 4]; c = [a, b]; d = copy.copy(c); id(c) 与 id(d) 不一致； id(c[0]) 与 id(d[0]) 一致
- 有两层数据类型，外层为可变数据类型，内层为不可变数据类型
  - a, b = (1, 2), (3, 4); c = [a, b]; d = copy.copy(c); id(c) 与 id(d) 不一致； id(c[0]) 与 id(d[0]) 一致
- 有两层数据类型，外层为不可变数据类型，内层为不可变数据类型; 外层地址不变， 内层地址不变
- 有两层数据类型，外层为不可变数据类型，内层为可变数据类型；外层地址不变，内层地址不变
## 深拷贝
- 有一层数据类型，且数据类型时可变数据类型，例如：列表、字典；import copy; a = [1, 2]; b = copy.deepcopy(a); id(a) 与 id(b) 地址发生改变
- 有一层数据类型，且数据类型时不可变数据类型，例如：元组、字符串； 地址未改变 （*）
- 有两层数据类型，外层为可变数据类型，内层为可变数据类型；外层地址改变，内层地址改变
- 有两层数据类型，外层为可变数据类型，内层为不可变数据类型；外层地址改变，内层地址改变
- 有两层数据类型，外层为不可变数据类型，内层为不可变数据类型； 外层地址不变，内层地址不变 （*）
- 有两层数据类型，外层为不可变数据类型，内层为可变数据类型； 外层地址改变，内层地址改变
## 总结
当内层为可变数据类型时，深拷贝后内层外、层地址均发生改变
当内层为不可变数据类型时，外层不管是可变还是不可变数据类型，使用深拷贝，都不会改变内层地址，只会在外层为可变数据类型时，改变外层地址;
使用浅拷贝是只能在外层数据类型为可变数据类型时，才能改变外层地址。而内层地址，无论是否为可变数据类型还是不可变数据类型，使用浅拷贝都不会改变内层数据类型地址;

# 进程、线程、协程
并发编程是实现多任务协同处理，改善系统性能的方式，Python 中实现并发编程主要依靠进程、线程和协程
进程是计算机中的程序关于某数据集合的一次运行实例，是操作系统资源分配的最小单位；
线程包含在进程中，是操作系统进行程序调度执行的最小单位；
协程是用户态执行的轻量级编程模型，由单一线程内部发出控制信号进行调度
协程常用于IO密集型工作，例如网络资源请求、磁盘存取等；而进程、线程常用于计算密集型工作，例如科学计算、人工神经网络等

进程拥有自己独立的堆和栈，既不共享堆，亦不共享栈，进程由操作系统调度
线程拥有自己独立的栈和共享的堆，共享堆，不共享栈，线程亦由操作系统调度
协程避免了无意义的调度，由此可以提高性能；但同时协程也失去了线程使用多CPU的能力
多线程用于IO密集型，进程用于CPU密集型任务
并发是一个人同时吃三个馒头，而并行是三个人同时吃三个馒头

通过 event = multiprocessing.Event() 事件，如果监控到 event.is_set 被设置，可以调用对应进程对象的 terminal 方法
通过 psutil.process_iter() 比较进程名称是否相等，然后调用进程的 kill() 方法
通过 python 执行系统命令 subprocess.call('ls'), os.systme('ls'), os.popen('ls').read()

## Python 多进程依赖标准库的进程类 mutiprocessing.Process
start() 创建一个 Process 子进程实例并执行该实例的 run() 方法
run() 子进程需要实现的目标任务
join() 主进程阻塞等待子进程，直到子进程结束才执行，可设置等待超时 timeout
terminate() 终止子进程
is_alive() 判断子进程是否终止
deamon 设置子进程是否随主进程退出而退出

## Python 多线程依赖标准库的线程类 threading.Thread
start()/run()/join()/is_alive()/daemon
可以通过线程锁 lock = threading.Lock()  lock.acquire()  lock.release() 进行数据同步，包含共享资源；也可通过 with 进行自动释放

# 状态机，FSM Finite-state machine，有限状态自动机
表示有限个状态，以及在这些状态之间的转移和动作等行为的数学模型，一般可以用状态图来对状态机进行精确地描述
transitions 是 python 的一个有限状态机设计库
状态机需要含有两个要素：state 状态结点；transiton 状态转移，表示由一个状态转移到另一个状态

# dataclass
一个类，其属性均可公开访问，且类中含有与这些属性相关的类方法
即，是一个含有数据及操作数据方法的容器
- 与普通 class 比较，dataclass 不包含私有属性，数据都可以直接访问
- 有固定的 repr 方法，打印出类名和属性和属性的值
- 拥有 __eq__ 和 __hash__ 方法，但是 __hash__ 返回 None，即不可哈希，不能作为字典的键
- 有着单一固定的构造方式，或是需要重载运算符，而不同的 class 无需
- 比 namedtuple 更灵活，他可以有类继承的便利，可以进行继承
```
from dataclasses import dataclass
@dataclass
class A:
    name: str
    age: int
    def info(self) -> str:
        return f"name={name},age={age}"
```
- 自动根据注解，完成 __init__ 的工作，及 __repr__ 和 __eq__
- 使用 dataclasses.asdic t和 dataclasses.astuple 我们可以把数据类实例中的数据转换成字典或者元组

# 迭代器
实现了方法__iter__的对象是可迭代的，返回自身
实现了方法__next__的对象是迭代器
```
class TestIterator:
    value=0

    def __next__(self):
        self.value +=1
        if self.value > 10:
            raise StopIteration  # 如果迭代器没有可供返回的值，应引发StopIteration异常
        return self.value

    def __iter__(self):
        return self
 
t = TestIterator()
print(t)  # <__main__.TestIterator object at 0x0000020286644CD0>
print(next(t), next(t))  # 1 2  使用内置函数next
print(list(t))  # [3, 4, 5, 6, 7, 8, 9, 10] 使用构造函数list显示地将迭代器转化为列表
```
包含yield语句的函数被称为生成器
生成器和普通函数的区别在于，生成器不是使用return返回一个值，而是可以生成多个值，每次一个
每次使用yield生成一个值后，函数都将停止执行，等待被重新唤醒。重新换新后将从停止的地方开始继续执行
```
def simple_generator():
    yield 1
    yield 2
print(simple_generator)  # 包含yield 就是一个生成器函数<function simple_generator at 0x000001590F5304A0>
print(simple_generator())  # 返回的是一个生成器对象 <generator object simple_generator at 0x000001590F4E8880>
a = simple_generator()
print(next(a), next(a))  # 1 2 生成器对象使用和迭代器一样的 next 进行使用
```
迭代：访问集合元素的一种方式，可以遍历集合中的所有元素，例如我们使用的for循环来遍历列表
迭代的好处：节省内存空间，迭代是读取多少元素，就将多少元素装载到内存中，不读取就不装
可迭代对象：实现了__iter__方法，该方法会返回一个迭代器对象
迭代器：如果在一个类中定义__iter__方法和__next__方法
生成器：如果一个函数中使用了yield关键字

# 元类
对象的类型是类，类的类型是元类
可以方便的控制类属性和类实例方法的创建过程，即干涉类的创建过程
## 通过元类实现单例模式
创建类时显式的指定类的metaclass，而自定义的metaclass继承type，并重新实现__call__方法
type 是默认的元类（内建元类，metaclass)，自定义的元类必须继承自 type，即继承了构建类的能力
__new__ 负责类的创建，返回一个实例，通过类名实例化的时候自动调用
__init__ 负责对 __new__ 实例化的对象进行初始化，每次实例化之后自动调用
__call__ 声明这个类对象是可调用的，但是，在元类中还负责了对象的创建，即元类中需要重新定义
```
class Singleton(type):
    def __init__(cls, *args, **kwargs):  # 编写元类时，通常会把self参数改为cls，这样能更清楚的表明要构建的实例是类
        cls.__instance = None
        super().__init__(*args, **kwargs)
    def __call__(cls, *args, **kwargs):  # 编写元类时，通常会把self参数改为cls，这样能更清楚的表明要构建的实例是类
        if cls.__instance is None:
            cls.__instance = super().__call__(*args, **kwargs)
        return cls.__instance
class Test(metaclass=Singleton):
    # __metaclass__ = Singleton 也可通过属性设置，会先从类的 __metaclass__ 属性查询，然后从父类的 __metaclass__ 查询
    # 如果父类没有，且解释器中也没有全局 __metaclass__ 变量，这个类就是传统类，会用 type.ClassType 作为此类的元类
    def __init__(self):
        pass
a, b = Test(), Test()
print(id(a), id(b))
```
## type 也是一个类，也可以通过 type 创建类
type(name, base, attrs) 
Foo = type("Foo", (), {"bar": True}) 等价于 class Foo(object) bar = True
FooChild = type("FooChild", (Foo,), {}) 可以继承
## 通过元类实现 ORM
```
class Field(object):
    def __init__(self, name, column_type):
        self.name = name
        self.column_type = column_type
    def __str__(self):
        return "<%s %s %s>"%(self.__class__.__name__, self.name, self.column_type)
class StringField(Field):
    def __init__(self, name):
        super(StringField, self).__init__(name, "varchar(255)")
class ModelMetaclass(type):
    def __new__(cls, name, bases, attrs):
        if name == "Model":
            return type.__new__(cls, name, bases, attrs)
        print("Fond Model: %s"% name)
        mappings = {}  # 查找Field字段
        for k, v in attrs.items():
            if isinstance(v, Field):
                print("Fond Field: %s => %s"% (k, v))
                mappings[k] = v
        for k in mappings.keys():  # 弹出Field字段
            attrs.pop(k)
        attrs["__mappings__"] = mappings  # 保存属性和列的映射关系
        attrs["__table__"] = name   # 假设表名和类名一致
        return type.__new__(cls, name, bases, attrs)
class Model(dict, metaclass=ModelMetaclass):
    def __init__(self, **kwargs):
        super(Model, self).__init__(**kwargs)
    def __getattr__(self, key):
        return self[key]
    def __setattr__(self, key, value):
        self[key] = value
    def save(self):
        fields = []
        params = []
        args = []
        for k, v in self.__mappings__.items():
            fields.append(v.name)
            params.append("?")
            args.append(getattr(self, k, None))
        sql = "insert into %s (%s) VALUES (%s)"% (self.__table__, ",".join(fields), ",".join(params))
        print("sql: %s"% sql)
        print("args: %s"% args)
class User(Model):
    # 定义类的属性到列的映射：
    id = IntegerField("id")
    name = StringField("name")
    email = StringField("email")
    password = StringField("password")
if __name__ == '__main__':
    # # 创建一个实例
    user = User(id=1, name="Tom", email="12345@qq.com", password="123456")
    # 保存到数据库
    user.save()
    # 访问元素
    print(user.name)
```

# 描述器
动态查找、托管属性、定制名称
描述器让对象能够自定义属性查找、存储和删除的操作；
描述器是一个类，且实现了下面方法中的任意一个，__get__()/__set__()/__delete__()
(描述器是一个包含绑定行为的对象，对其属性的存取被描述器协议中定义的方法覆盖)
对象属性的访问顺序：实例的 __dict__、类的 __dict__、基类的 __dict__，如果找到的是定义了某个描述器方法的对象，
则 Python 可能会重载默认方法并转而发起调用描述器方法
- 如果一个类，仅定义了 __get__ 的描述器叫做非资料描述器
- 如果一个类同时定义了 __get__/__set__ 的描述器叫做资料描述器
- 优先级不同：如果实例自动中有描述器同名的属性，如果是资料描述器，则优先使用资料描述器，如果是非资料描述器，优先使用字典中的属性
描述器只对新式类和新式对象才起作用，即继承至 object 的类
重写 __getattribute__() 会改变所有属性的访问行为，如果只对某些属性的行为感兴趣，使用描述器是最好的方案
## 属性 property 是建立资料描述器的一种简洁方式，可以在访问属性的时候触发相应的方法调用
```
class C(object):
    def getx(self): return self.__x
    def setx(self, value): self.__x = value
    def delx(self): del self.__x
    x = property(getx, setx, delx, "I'm the 'x' property.")
```
## 验证器类，阻止无效对象的创建
是一个用于托管属性访问的描述器。在存储任何数据之前，它会验证新值是否满足各种类型和范围限制
如果不满足这些限制，它将引发异常，从源头上防止数据损坏
```
from abc import ABC, abstractmethod
class Validator(ABC):
    def __set_name__(self, owner, name):
        self.private_name = '_' + name
    def __get__(self, obj, objtype=None):
        return getattr(obj, self.private_name)
    def __set__(self, obj, value):
        self.validate(value)
        setattr(obj, self.private_name, value)
    @abstractmethod
    def validate(self, value):
        pass
```
自定义验证器需要从 Validator 继承，并且必须提供 validate() 方法以根据需要测试各种约束
```
class Number(Validator):
    def __init__(self, minvalue=None, maxvalue=None):
        self.minvalue = minvalue
        self.maxvalue = maxvalue
    def validate(self, value):
        if not isinstance(value, (int, float)):
            raise TypeError(f'Expected {value!r} to be an int or float')
        if self.minvalue is not None and value < self.minvalue:
            raise ValueError(
                f'Expected {value!r} to be at least {self.minvalue!r}'
            )
        if self.maxvalue is not None and value > self.maxvalue:
            raise ValueError(
                f'Expected {value!r} to be no more than {self.maxvalue!r}'
            )
```
## ORM，通过描述器进行查找和更新
```
class Field:
    def __set_name__(self, owner, name):
        self.fetch = f'SELECT {name} FROM {owner.table} WHERE {owner.key}=?;'
        self.store = f'UPDATE {owner.table} SET {name}=? WHERE {owner.key}=?;'
    def __get__(self, obj, objtype=None):
        return conn.execute(self.fetch, [obj.key]).fetchone()[0]
    def __set__(self, obj, value):
        conn.execute(self.store, [value, obj.key])
        conn.commit()
class Movie:
    table = 'Movies'                    # Table name
    key = 'title'                       # Primary key
    director = Field()
    year = Field()
    def __init__(self, key):
        self.key = key
import sqlite3
conn = sqlite3.connect('entertainment.db')
Movie('Star Wars').director
```

# AOP 与装饰器
AOP，就是面向切面编程，简单的说，就是动态地将代码切入到类的指定方法、指定位置上的编程思想就是面向切面的编程。

我们管切入到指定类指定方法的代码片段称为切面，而切入到哪些类、哪些方法则叫切入点。这样我们就可以把几个类共有的代码，抽取到一个切片中，等到需要时再切入对象中去，从而改变其原有的行为。

这种思想，可以使原有代码逻辑更清晰，对原有代码毫无入侵性，常用于像权限管理，日志记录，事物管理等等。

而Python中的装饰器就是很著名的设计

# Python垃圾回收机制
Python GC主要使用引用计数（reference counting）来跟踪和回收垃圾;
在引用计数的基础上，通过“标记-清除”（mark and sweep）解决对象可能产生的循环引用问题;
通过“分代回收”（generation collection）以空间换时间的方法提高垃圾回收效率。
## 引用计数
PyObject是每个对象必有的内容，其中ob_refcnt就是做为引用计数;
当一个对象有新的引用时，它的ob_refcnt就会增加，当引用它的对象被删除，它的ob_refcnt就会减少;
引用计数为0时，该对象生命就结束了;
优点:简单，实时性
缺点:维护引用计数消耗资源，循环引用
## 标记-清除机制
基本思路是先按需分配，等到没有空闲内存的时候从寄存器和程序栈上的引用出发，
遍历以对象为节点、以引用为边构成的图，把所有可以访问到的对象打上标记，然后清扫一遍内存空间，把所有没标记的对象释放
## 分代技术
将系统中的所有内存块根据其存活时间划分为不同的集合，每个集合就成为一个“代”，
垃圾收集频率随着“代”的存活时间的增大而减小，存活时间通常利用经过几次垃圾回收来度量
Python默认定义了三代对象集合，索引数越大，对象存活时间越长
举例： 当某些内存块M经过了3次垃圾收集的清洗之后还存活时，我们就将内存块M划到一个集合A中去，而新分配的内存都划分到集合B中去。当垃圾收集开始工作时，大多数情况都只对集合B进行垃圾回收，而对集合A进行垃圾回收要隔相当长一段时间后才进行，这就使得垃圾收集机制需要处理的内存少了，效率自然就提高了。在这个过程中，集合B中的某些内存块由于存活时间长而会被转移到集合A中，当然，集合A中实际上也存在一些垃圾，这些垃圾的回收会因为这种分代的机制而被延迟

# ssh
## create
ssh-keygen -t rsa -b 4096
ssh-keygen -t rsa -b 4096 -C "nfs_fly@163.com"
将本地的 id_rsa.pub 追加到远程主机的 authorized_keys 中
## login
ssh root@66.112.123.123 -p 27
## ssh config 文件格式
"""
Host dev
    HostName 66.112.123.123
    Port 27
    User root
    IdentityFile id_rsa   
"""
## git 免密登录
ssh-copy-id -i ~/.ssh/id_rsa.pub root@192.163.0.0
scp .ssh/id_rsa.pub root@192.163.0.0:~/home
cat ~/home/id_rsa.pub >> ~/.ssh/authorized_keys

# Anaconda的安装步骤
① 图形界面安装 ② 命令行安装 ③ windows 下的命令行 Anaconda Prompt
```
① 在终端中输入命令 conda list ，如果Anaconda被成功安装，则会显示已经安装的包名和版本号。在“Advanced Installation Options”中不要勾选“Add Anaconda to my PATH environment variable.”（“添加Anaconda至我的环境变量。”）。因为如果勾选，则将会影响其他程序的使用。如果使用Anaconda，则通过打开Anaconda Navigator或者在开始菜单中的“Anaconda Prompt”（类似macOS中的“终端”）中进行使用。除非你打算使用多个版本的Anaconda或者多个版本的Python，否则便勾选“Register Anaconda as my default Python 3.6”
② “开始 → Anaconda3（64-bit）→ 右键点击Anaconda Prompt → 以管理员身份运行”，在Anaconda Prompt中输入 conda list ，可以查看已经安装的包名和版本号。若结果可以正常显示，则说明安装成功

验证conda已被安装 conda --version
更新conda至最新版本 conda update conda
查看conda帮助信息 conda -- help 或 conda -h

创建新环境 conda create --name <env_name> <package_names>
如： conda create --name python2 python=2.7 ，即创建一个名为“python2”的环境，环境中安装版本为2.7的python。
如： conda create -n python3 python=3.5 numpy pandas ，即创建一个名为“python3”的环境，环境中安装版本为3.5的python，同时也安装了numpy和pandas。--name 同样可以替换为 -n 提示：默认情况下，新创建的环境将会被保存在 /Users/<user_name>/anaconda3/env 目录下

切换环境
① Linux 或 macOS  source activate <env_name>
② Windows  activate <env_name>

退出环境至root
① Linux 或 macOS  source deactivate
② Windows  deactivate

显示已创建环境
conda info --ENVS 或 conda info -e 或 conda env list

复制环境
conda create --name <new_env_name> --clone <copied_env_name>

删除环境
conda remove --name <env_name> --all

管理包
1. 查找可供安装的包版本
① 精确查找 conda search --full-name <package_full_name>
② 模糊查找
conda search <text>
2.获取当前环境中已安装的包信息
conda list

安装包
① 在指定环境中安装包
conda install --name <env_name> <package_name>
② 在当前环境中安装包
conda install <package_name>
③ 使用pip安装包
当使用 conda install 无法进行安装时，可以使用pip进行安装。例如：see包
pip install <package_name>

卸载包
① 卸载指定环境中的包
conda remove --name <env_name> <package_name>
② 卸载当前环境中的包
conda remove <package_name>

更新包
① 更新所有包 conda update --all
或 conda upgrade --all
② 更新指定包
conda update <package_name> 或 conda upgrade <package_name>

在.contact 中配置国内源
channels:
  - defaults
show_channel_urls: true
default_channels:
  - http://mirrors.aliyun.com/anaconda/pkgs/main
  - http://mirrors.aliyun.com/anaconda/pkgs/r
  - http://mirrors.aliyun.com/anaconda/pkgs/msys2
custom_channels:
  conda-forge: http://mirrors.aliyun.com/anaconda/cloud
  msys2: http://mirrors.aliyun.com/anaconda/cloud
  bioconda: http://mirrors.aliyun.com/anaconda/cloud
  menpo: http://mirrors.aliyun.com/anaconda/cloud
  pytorch: http://mirrors.aliyun.com/anaconda/cloud
  simpleitk: http://mirrors.aliyun.com/anaconda/cloud

conda clean -I  清除索引缓存
```

# scrapy 五大核心组件及作用
框架封装的组件丰富，适用于开发大规模的抓取项目;框架基于 Twisted 异步框架，异步处理请求，更快捷，更高效;拥有强大的社区支持，拥有丰富的插件来扩展其功能
 简述多页爬取的思路
思路一：将所有的页面 url 生成后放在 start_urls 中，当项目启动后会对 start_urls 中的 url 发起请求，实现多页爬取
思路二：在解析方法中构建 url，使用 scrapy 手动发送请求并指定回调，实现多页爬取
Scrapy 框架管道必须实现的方法是 process_item
(1) 引擎：负责各个组件之间的通讯信号及数据的传递
(2) 调度器：接受引擎传递的 request，并整理排列，然后进行请求的调度
(3) 下载器：负责下载 request，提交响应给引擎，引擎传递给 spider
(4) 爬虫：定义了爬取行为和解析规则，提交 item 并传给管道
(5) 管道: 负责处理 spider 传递来 的 item，如 去重、持久化存储等

# Python 中的反射吗
通过字符串映射对象 object 的方法或者属性
hasattr(obj,name_str): 判断objec是否有name_str这个方法或者属性
getattr(obj,name_str): 获取object对象中与name_str同名的方法或者函数
setattr(obj,name_str,value): 为object对象设置一个以name_str为名的value方法或者属性
delattr(obj,name_str): 删除object对象中的name_str方法或者属性

# mysql 一张学生表，包含姓名、科目、成绩，找出平均分数大于60的学生
"""
    select 
        Id as 编号，
        name as 姓名，
        sum(score) as 总成绩，
        sum(score) / count(subject) as 平均成绩
    from 
        student_table
    group by  
        name
    having  # 对分组结果进行筛选
        sum(score) / count(subject) > 60
"""
计算各科成绩大于平均

# Docker 是一种容器技术，解决软件跨环境迁移的问题
## 容器与虚拟机比较，Docker 启动速度快、占用体积小
- 虚拟机是一个计算机系统的仿真，简单来说，虚拟机可以实现在一台物理计算机上模拟多台计算机运行任务
  - 操作系统和应用共享一台或多台主机(集群)的硬件资源，每台VM有自己的OS，硬件资源是虚拟化
  - 管理程序(hypervisor)负责创建和运行VM，它连接了硬件资源和虚拟机，完成server的虚拟化
  - 每个虚拟机不仅运行一个 OS 的完整拷贝，并且需要所有硬件的虚拟化拷贝，消耗大量的内存和 CPU
- 容器将操作系统进行虚拟化，在操作系统之上，每个容器共享 OS 内核、执行文件和库等
  - 容器非常的轻量，仅 MB 水平且几秒就可启动
  - 容器可以帮助创建一个可以移植的、一致的开发、测试和部署环境
- 镜像 Image 就是一堆只读层 read-only layer，每层就是一个文件系统，整个文件系统称为统一文件系统 union-file system
- 通过 Image 创建容器 Container，容器是镜像创建的运行实例，可以被启动、开始、停止、删除，每个容器相互隔离、保证安全
  - 容器是在原先的 Image 之上新加一层，称为 Container Layer，可读可写（Image 是只读），容器 = 镜像 + 读写层
  - Image 负责 App 的存储和分发，Container 负责运行 App
- 仓库/注册中心，是集中存放 Image 的场所 

1： 自己发展 这个岗位工作中的职责和侧重的方向
            岗位发展是什么样的，未来有没有其他的发展方向
            团队人员配备，平常的工作流程是怎样的

2： 公司发展 直属领导的做事风格怎样，团队氛围是什么样的 
            公司的发展方向和前景是怎么样的
            公司的商业模式，有没有哪些竞品公司和他们比又怎么样呢

3： 试用期时间和工资、公积金比例

规划：我本科和研究生都是读的计算机相关的专业，毕业之后也一直在从事相关的工作，我会一直坚持下去，上家单位有不到三年的时间，
积累了一部分行业知识，也沉淀了自己的技术能力，下一份工作我希望是能有一个大的平台，能够在岗位上独立负责、解决问题，成为技术核心、核心开发者

无论什么时候，我们都应该把大部分的诗句放在提升自己
剩下的顺气自然，对任何人不抱有过分的期待，没有期待就没有失望，
得到的就当做是惊喜，得不到的也是常态，不要因为一个人的对你的伤害和否定，就否定自己的未来
真诚和善良永远都没有错，错的是你没有分清对象，所以你该反思的是自己看人的眼光和见识，
而不是自己的真诚和善良，当每个人真正强大起来的时候，都要度过一段没有人帮忙，没有人支持的日子，
所有的事情都是一个人在撑，所有的情绪只有自己知道，但你咬牙撑过去熬过去就都不一样了，
烦躁的时候不要说话，不要做决定，自己安静的走一回儿，这些难推的事情，你总要学会自己消化掉，
毕竟青春只有一次，请你热烈又勇敢
