# 操作系统机制与后端开发映射矩阵 (Backend Mappings)

> **原则**：学习操作系统不是背诵生硬概念，而是为了透彻理解后端高并发、网络 I/O、JVM 内存与存储引擎在底层的真实运行原理。

---

## 1. 操作系统核心主题池

### P0：后端面试必考与高频机制（优先攻坚）
- **进程 vs 线程 vs 协程**：资源分配单位 vs CPU 调度单位，PCB 结构，用户级线程与内核级轻量级进程。
- **上下文切换 (Context Switch) 代价**：CPU 寄存器保存、页表基址切换、CPU L1/L2 Cache 失效与 TLB 冲刷。
- **用户态与内核态**：Ring 0 vs Ring 3 权限级别，中断、异常与系统调用（System Call）的工作原理。
- **并发同步机制**：临界区、互斥锁 (Mutex)、信号量 (Semaphore)、自旋锁 (Spinlock) 的底层代价与选型。
- **死锁四大必要条件**：互斥、占有且等待、不可抢占、循环等待，以及破坏策略与资源有序分配法。
- **虚拟内存与分页**：逻辑地址到物理地址映射、页表 (Page Table)、TLB 快表加速、缺页异常 (Page Fault) 与页面置换。

### P1：Linux 系统与后端深度强关联
- **进程虚拟地址空间**：代码段、数据段、BSS、堆（从低到高）、内存映射区 (mmap)、栈（从高到低）。
- **文件系统与 I/O 抽象**：一切皆文件、文件描述符表 (FD Table)、系统级打开文件表、inode 结构。
- **I/O 模型演进**：阻塞 I/O、非阻塞 I/O、I/O 多路复用（`select` / `poll` / `epoll` 的红黑树与就绪链表机制）。
- **零拷贝技术 (Zero-Copy)**：传统 4 次上下文切换 + 4 次拷贝 vs `mmap` / `sendfile` 的 DMA 直接内存拷贝。

### P2：课程理论补充（按需查阅）
- 经典 CPU 调度算法细节（FCFS、SJF、多级反馈队列）。
- 银行家算法矩阵计算。
- 磁盘调度算法（SCAN、C-SCAN）。

---

## 2. Java / 后端实战深度映射

在学习 OS 机制时，优先联系真实的后端生产场景：

| 操作系统底层机制 | 对应 Java / 后端生产场景 | 典型追问与面试切入点 |
| :--- | :--- | :--- |
| **OS 原生线程 (pthread)** | Java `Thread` 与线程池 (`ThreadPoolExecutor`) | 为什么不能无脑创建数万个 Java 线程？上下文切换开销如何观测？ |
| **内核互斥锁 (Futex)** | Java `synchronized` 与 `ReentrantLock` | 锁膨胀机制（偏向锁/轻量级锁/重量级锁）如何与 OS 用户态自旋及内核挂起结合？ |
| **进程虚拟地址空间** | JVM 运行时数据区（堆、元空间、直接内存） | JVM 堆外内存泄露排查与 Linux `cat /proc/<PID>/maps` 观测。 |
| **文件描述符与 Socket** | Tomcat / Netty 网络传输层 | “Too many open files” 是如何发生的？Netty 为什么选择 epoll 边缘触发？ |
| **I/O 多路复用 (epoll)** | Redis 单线程模型高性能之谜 | Redis 为什么单线程还能达到 10w+ QPS？事件循环 (Event Loop) 如何处理 FD？ |
| **页缓存 (Page Cache) 与磁盘** | MySQL InnoDB Buffer Pool 与 Redo Log | 为什么脏页刷盘需要顺序写？`fsync` 系统调用如何保障数据持久性？ |
| **进程命名空间与 cgroup** | Docker 容器隔离与资源配额 | 容器是虚拟机吗？容器里的 PID 1 到底是什么？ |
