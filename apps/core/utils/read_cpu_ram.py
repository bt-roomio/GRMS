import psutil


def get_cpu_usage(seconds=2):
    return psutil.cpu_percent(seconds)


def get_ram_usage():
    return psutil.virtual_memory()[2]
