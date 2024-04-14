# ** 1、初始化 **
import comfy.options
comfy.options.enable_args_parsing()     # 用来配置某些全局选项，并接受命令行参数

import os
import importlib.util       # 动态加载模块
import folder_paths         # 定制的文件夹路径模块
import time


# ** 2、工具函数 **
def execute_prestartup_script():
    """
    工具函数：目的是在程序的其他主要部分启动前，执行特定目录下的每个 `prestartup_script.py` 文件
    主要逻辑：
        1、构造辅助函数：动态构造模块的路径，尝试加载并执行模块
        2、查找并加载自定义节点：查找所有节点，并执行其 `prestartup_script.py` 文件
        3、打印自定义节点执行状态：标记节点是否加载成功，以及加载耗时等信息
    """
    # 辅助功能：动态构造模块的路径，尝试加载并执行模块，如果失败则捕获异常并返回False，成功则返回True
    def execute_script(script_path):
        module_name = os.path.splitext(script_path)[0]
        try:
            spec = importlib.util.spec_from_file_location(module_name, script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return True
        except Exception as e:
            print(f"Failed to execute startup-script: {script_path} / {e}")
        return False

    #  在 `custom_nodes` 目录中查找所有节点，并执行其 `prestartup_script.py` 文件
    node_paths = folder_paths.get_folder_paths("custom_nodes")
    for custom_node_path in node_paths:
        possible_modules = os.listdir(custom_node_path)
        node_prestartup_times = []

        for possible_module in possible_modules:
            module_path = os.path.join(custom_node_path, possible_module)
            if os.path.isfile(module_path) or module_path.endswith(".disabled") or module_path == "__pycache__":
                continue

            script_path = os.path.join(module_path, "prestartup_script.py")
            if os.path.exists(script_path):
                time_before = time.perf_counter()
                success = execute_script(script_path)
                node_prestartup_times.append((time.perf_counter() - time_before, module_path, success))

    # 打印出执行每个启动脚本所花费的时间，并注明脚本是否执行成功。
    if len(node_prestartup_times) > 0:
        print("\nPrestartup times for custom nodes:")
        for n in sorted(node_prestartup_times):
            if n[2]:
                import_message = ""
            else:
                import_message = " (PRESTARTUP FAILED)"
            print("{:6.1f} seconds{}:".format(n[0], import_message), n[1])
        print()

execute_prestartup_script()


# 程序的主要部分启动
import asyncio          # 异步I/O操作
import itertools        # 交互算法
import shutil           # 文件系统操作
import threading        # 线程处理
import gc               # 垃圾回收

from comfy.cli_args import args         # 命令行参数的一个实例
import logging

if os.name == "nt":
    logging.getLogger("xformers").addFilter(lambda record: 'A matching Triton is not available' not in record.getMessage())

if __name__ == "__main__":
    # 设置 CUDA 设备和散列库的工作配置
    if args.cuda_device is not None:
        os.environ['CUDA_VISIBLE_DEVICES'] = str(args.cuda_device)
        logging.info("Set cuda device to: {}".format(args.cuda_device))

    # 检测Windows系统日志有效性
    if args.deterministic:
        if 'CUBLAS_WORKSPACE_CONFIG' not in os.environ:
            os.environ['CUBLAS_WORKSPACE_CONFIG'] = ":4096:8"

    # 动态导入CUDA 动态内存分配相关的 `cuda_malloc`模块
    import cuda_malloc


import comfy.utils
import yaml

import execution
import server
from server import BinaryEventTypes
from nodes import init_custom_nodes
import comfy.model_management


def cuda_malloc_warning():
    device = comfy.model_management.get_torch_device()
    device_name = comfy.model_management.get_torch_device_name(device)
    cuda_malloc_warning = False
    if "cudaMallocAsync" in device_name:
        for b in cuda_malloc.blacklist:
            if b in device_name:
                cuda_malloc_warning = True
        if cuda_malloc_warning:
            logging.warning("\nWARNING: this card most likely does not support cuda-malloc, if you get \"CUDA error\" please run ComfyUI with: --disable-cuda-malloc\n")


def prompt_worker(q, server):
    """
    功能：用于处理执行prompt指令：应对请求进行有序处理，监控内存使用情况，并按需进行垃圾收集(gc)以释放资源
    :param q: 一个消息队列，服务器用它来接收待处理的指令。
    :param server: 服务器实例，处理指令和管理状态。
    """
    # 创建一个执行器实例`e`，负责执行指令
    e = execution.PromptExecutor(server)
    last_gc_collect = 0
    need_gc = False
    gc_collect_interval = 10.0

    # 进入一个无限循环，从`q`队列中取出并执行指令。
    while True:
        timeout = 1000.0
        if need_gc:
            # 根据垃圾收集需求，调整队列获取超时`timeout`
            timeout = max(gc_collect_interval - (current_time - last_gc_collect), 0.0)

        # 从队列`q`中获取元项`queue_item`以及变量
        queue_item = q.get(timeout=timeout)
        if queue_item is not None:
            item, item_id = queue_item
            execution_start_time = time.perf_counter()
            prompt_id = item[1]      # `prompt_id`来确定附加特性，在执行前记录当前时间(`execution_start_time`)
            server.last_prompt_id = prompt_id

            # 执行指令，并宣布任务完成，输出结果记入日志。
            e.execute(item[2], prompt_id, item[3], item[4])
            need_gc = True
            q.task_done(item_id,
                        e.outputs_ui,
                        status=execution.PromptQueue.ExecutionStatus(
                            status_str='success' if e.success else 'error',
                            completed=e.success,
                            messages=e.status_messages))
            if server.client_id is not None:
                server.send_sync("executing", {"node": None, "prompt_id": prompt_id}, server.client_id)

            current_time = time.perf_counter()
            execution_time = current_time - execution_start_time
            logging.info("Prompt executed in {:.2f} seconds".format(execution_time))

        # 其中`flags`字典可能提供信息，指示是否应释放内存或卸载模型。
        flags = q.get_flags()
        free_memory = flags.get("free_memory", False)

        if flags.get("unload_models", free_memory):
            comfy.model_management.unload_all_models()
            need_gc = True
            last_gc_collect = 0

        if free_memory:
            e.reset()
            need_gc = True
            last_gc_collect = 0

        if need_gc:
            # 如果需要，执行垃圾收集，则会调用相关函数释放资源。
            current_time = time.perf_counter()
            if (current_time - last_gc_collect) > gc_collect_interval:
                comfy.model_management.cleanup_models()
                gc.collect()
                comfy.model_management.soft_empty_cache()
                last_gc_collect = current_time
                need_gc = False

async def run(server, address='', port=8188, verbose=True, call_on_start=None):
    """
    异步函数：启动服务器的异步监听循环。
    """
    # `asyncio.gather`用以并行运行服务器和发布循环，这使得服务器能接收和处理来自不同来源的多个指令。
    await asyncio.gather(server.start(address, port, verbose, call_on_start), server.publish_loop())


def hijack_progress(server):
    """
    监听函数：监视长时间执行的指令过程的进度，并在有效的时候发送回馈到客户端。
    """
    # 覆写全局进度条的钩子函数
    def hook(value, total, preview_image):
        """
        功能：每当进度更改的时候，会调用这个函数来发送实时进度消息给客户端，可通过`server.send_sync`同步发送。
        """
        comfy.model_management.throw_exception_if_processing_interrupted()
        progress = {"value": value, "max": total, "prompt_id": server.last_prompt_id, "node": server.last_node_id}

        server.send_sync("progress", progress, server.client_id)
        if preview_image is not None:
            server.send_sync(BinaryEventTypes.UNENCODED_PREVIEW_IMAGE, preview_image, server.client_id)

    comfy.utils.set_progress_bar_global_hook(hook)


# 清理临时使用
def cleanup_temp():
    temp_dir = folder_paths.get_temp_directory()
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)


# 读取并加载YAML配置文件来增加额外的模型搜索路径。
def load_extra_path_config(yaml_path):
    with open(yaml_path, 'r') as stream:
        config = yaml.safe_load(stream)
    for c in config:
        conf = config[c]
        if conf is None:
            continue
        base_path = None
        if "base_path" in conf:
            base_path = conf.pop("base_path")
        for x in conf:
            for y in conf[x].split("\n"):
                if len(y) == 0:
                    continue
                full_path = y
                if base_path is not None:
                    full_path = os.path.join(base_path, full_path)
                logging.info("Adding extra search path {} {}".format(x, full_path))
                folder_paths.add_model_folder_path(x, full_path)


# ** 3、主代码 **
if __name__ == "__main__":
    # 设置临时目录、清理临时目录、读取和处理额外模型路径配置
    if args.temp_directory:
        temp_dir = os.path.join(os.path.abspath(args.temp_directory), "temp")
        logging.info(f"Setting temp directory to: {temp_dir}")
        folder_paths.set_temp_directory(temp_dir)
    cleanup_temp()

    # 如果需要，更新Windows更新程序(`new_updater`)。
    if args.windows_standalone_build:
        try:
            import new_updater
            new_updater.update_windows_updater()
        except:
            pass

    # 初始化异步事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # 创建服务
    server = server.PromptServer(loop)
    # 创建任务队列实例
    q = execution.PromptQueue(server)

    extra_model_paths_config_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "extra_model_paths.yaml")
    if os.path.isfile(extra_model_paths_config_path):
        load_extra_path_config(extra_model_paths_config_path)

    if args.extra_model_paths_config:
        for config_path in itertools.chain(*args.extra_model_paths_config):
            load_extra_path_config(config_path)

    init_custom_nodes()         # 初始化节点
    cuda_malloc_warning()       # cuda malloc相关警告
    server.add_routes()         # 添加路由
    hijack_progress(server)     # 监视进度

    # 服务器的背景执行程序：初始化并启动了一个线程`prompt_worker`，执行队列中的任务
    threading.Thread(target=prompt_worker, daemon=True, args=(q, server,)).start()

    # 使用外部参数配置输出目录
    if args.output_directory:
        output_dir = os.path.abspath(args.output_directory)
        logging.info(f"Setting output directory to: {output_dir}")
        folder_paths.set_output_directory(output_dir)

    # 设置节点存储的路径配置
    # 节点：当使用CheckpointSave等时，这些checkpoints、clip、vae模型将被保存到的默认文件夹。
    folder_paths.add_model_folder_path("checkpoints", os.path.join(folder_paths.get_output_directory(), "checkpoints"))
    folder_paths.add_model_folder_path("clip", os.path.join(folder_paths.get_output_directory(), "clip"))
    folder_paths.add_model_folder_path("vae", os.path.join(folder_paths.get_output_directory(), "vae"))

    # 使用外部参数配置输入目录
    if args.input_directory:
        input_dir = os.path.abspath(args.input_directory)
        logging.info(f"Setting input directory to: {input_dir}")
        folder_paths.set_input_directory(input_dir)

    if args.quick_test_for_ci:
        exit(0)

    call_on_start = None
    # 如果需要，进行autolaunch相关逻辑
    if args.auto_launch:
        def startup_server(address, port):
            import webbrowser
            if os.name == 'nt' and address == '0.0.0.0':
                address = '127.0.0.1'
            webbrowser.open(f"http://{address}:{port}")
        call_on_start = startup_server

    # 最终：异步启动服务器
    try:
        loop.run_until_complete(run(server,
                                    address=args.listen,
                                    port=args.port,
                                    verbose=not args.dont_print_server,
                                    call_on_start=call_on_start))
    except KeyboardInterrupt:
        logging.info("\nStopped server")

    cleanup_temp()

"""
梳理：
    结合明显的模块和函数名看来，此为服务器端执行环节，主要集成了以下功能：
        1、命令行参数解析、
        2、动态GPU内存配置、
        3、模型加载、
        4、自定义节点脚本执行、
        5、线程与异步I/O操作等功能。
    此为，嵌点预处理工作，CUDA内存管理的特殊处理，以及捕获Python垃圾回收，是需要注意的地方。
    
    整段代码意图服务于`prompt_worker`功能，是处理并执行用户命令的核心逻辑。
    除此之外，还有从文件夹、配置文件动态加载数据和处理CUDA环境设置等准备起步工作，并关注资源的临时性使用和清理工作。
"""