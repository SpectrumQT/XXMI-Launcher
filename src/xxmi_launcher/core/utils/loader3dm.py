import ctypes as ct
from win32api import OpenProcess, CloseHandle, GetModuleHandle, GetProcAddress
from win32file import GetFileAttributesW
from win32process import VirtualAllocEx, WriteProcessMemory, VirtualFreeEx, CreateRemoteThread, GetExitCodeThread
from win32event import WaitForSingleObject
import pywintypes
from win32con import PROCESS_CREATE_THREAD, PROCESS_QUERY_INFORMATION, PROCESS_VM_OPERATION, PROCESS_VM_WRITE, PROCESS_VM_READ, MEM_COMMIT, MEM_RELEASE, MEM_RESERVE, PAGE_READWRITE, WAIT_TIMEOUT, WAIT_FAILED
import ctypes.wintypes as wt
INVALID_FILE_ATTRIBUTES = -1

# ----------------------------------------------------------------------------
# Injects a dll into a process using WriteProcessMemory
#
# Error codes:
# 100 - Process not found / cannot open
# 110 - Invalid DLL path
# 120 - Failed to resolve dll
# 130 - Failed to resolve LoadLibraryW
# 200 - Failed to allocate remote memory
# 300 - Failed to write DLL path
# 400 - Failed to create remote thread
# 500 - Injection thread timed out
# 510 - Injection thread wait failed
# 600 - DLL injection failed (LoadLibraryW returned None)
# 700 - Unknown error
def inject(pid: int, module_path: str, timeout: int = 15) -> int:
	exit_code = 0

	# Open process with minimal rights
	try:
		process = OpenProcess(PROCESS_CREATE_THREAD | PROCESS_QUERY_INFORMATION | PROCESS_VM_OPERATION | PROCESS_VM_WRITE | PROCESS_VM_READ, False, pid)
	except pywintypes.error as e:
		if e.winerror == 87:
			return 100
		else:
			raise e

	# Validate DLL path
	if not module_path or GetFileAttributesW(module_path) == INVALID_FILE_ATTRIBUTES:
		return 110

	# Resolve LoadLibraryW
	try:
		kernel32 = GetModuleHandle("kernel32.dll")
	except pywintypes.error as e:
		CloseHandle(process)
		if e.winerror == 126:
			return 120
		else:
			raise e
	try:
		load_library = GetProcAddress(kernel32, "LoadLibraryW")
	except pywintypes.error as e:
		CloseHandle(process)
		if e.winerror == 127:
			return 130
		else:
			raise e

	module_path_buf = ct.create_unicode_buffer(module_path)
	# Allocate memory to hold the module path
	try:
		memory = VirtualAllocEx(process, 0, ct.sizeof(module_path_buf), MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
	except pywintypes.error:
		CloseHandle(process)
		return 200

	# Write module path to allocated memory
	try:
		WriteProcessMemory(process, memory, module_path_buf)
	except pywintypes.error:
		VirtualFreeEx(process, memory, 0, MEM_RELEASE)
		CloseHandle(process)
		return 300

	# Create a thread in the process to load the module from path in memory
	try:	
		thread, _ = CreateRemoteThread(process, None, 0, load_library, memory, 0)
	except pywintypes.error:
		VirtualFreeEx(process, memory, 0, MEM_RELEASE)
		CloseHandle(process)
		return 400

	# Wait for completion
	wait_code = WaitForSingleObject(thread, timeout * 1000)

	if wait_code == WAIT_TIMEOUT:
		CloseHandle(thread)
		VirtualFreeEx(process, memory, 0, MEM_RELEASE)
		CloseHandle(process)
		return 500

	if wait_code == WAIT_FAILED:
		CloseHandle(thread)
		VirtualFreeEx(process, memory, 0, MEM_RELEASE)
		CloseHandle(process)
		return 510
	
	# Check LoadLibraryW result
	try:
		thread_exit_code = GetExitCodeThread(thread)
		if thread_exit_code == 0:
			exit_code = 600 # LoadLibrary failed
	except:
		exit_code = 700
		
	# Cleanup
	CloseHandle(thread)
	VirtualFreeEx(process, memory, 0, MEM_RELEASE)
	CloseHandle(process)

	return exit_code