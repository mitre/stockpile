import donut
import os
import shutil


async def donut_handler(services, args):
    _, file_name = await services.get('file_svc').find_file_path(args.get('file'), location='payloads')
    exe_path, donut_ext = _stage_compatible_executable(file_name)
    shellcode = donut.create(file=exe_path)
    _write_shellcode_to_file(shellcode, file_name)
    os.remove(exe_path)
    return donut_ext, donut_ext


def _write_shellcode_to_file(shellcode, file_name):
    try:
        with open(file_name, 'wb') as f:
            f.write(shellcode)
    except Exception as ex:
        print(ex)


def _stage_compatible_executable(file_name):
    dir_path, donut_ext = os.path.split(file_name)
    exe_path = os.path.join(dir_path, '%s.exe' % donut_ext.split('.')[0])
    shutil.copy(src=file_name, dst=exe_path)
    return exe_path, donut_ext
