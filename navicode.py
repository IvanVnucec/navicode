import urllib.request
import json
import os

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
MODEL = os.getenv("MODEL")
DEBUG = int(os.getenv("DEBUG", 0))

RESET, BOLD, DIM, BLUE, CYAN, GREEN, YELLOW, RED = (
    "\033[0m",
    "\033[1m",
    "\033[2m",
    "\033[34m",
    "\033[36m",
    "\033[32m",
    "\033[33m",
    "\033[31m",
)

def read(args):
    try:
        lines = enumerate(open(args["path"], encoding="utf-8").readlines())
        return "".join(f"{idx}| {line}" for idx, line in lines)
    except Exception as err:
        return f"error: {err}"

def write(args):
    try:
        open(args["path"], "w", encoding="utf-8").write(args["content"])
        return "File written successfully."
    except Exception as err:
        return f"error: {err}"

def list_dir(args):
    try:
        path = args["path"]
        items = os.listdir(path)
        output = []
        for item in sorted(items):
            full_path = os.path.join(path, item)
            if os.path.isdir(full_path):
                output.append(f"[{item}]")
            else:
                output.append(item)
        return "\n".join(output)
    except Exception as err:
        return f"error: {err}"

TOOLS = {
    "read": {
        "call": read,
        "schema": {
            "type": "function",
            "function": {
                "name": "read",
                "description": "Read file (absolute file path)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                    },
                    "required": ["path"]
                }
            }
        }
    },
    "write": {
        "call": write,
        "schema": {
            "type": "function",
            "function": {
                "name": "write",
                "description": "Write content to a file (absolute or relative to cwd)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"},
                        "content": {"type": "string"},
                    },
                    "required": ["path", "content"]
                }
            }
        }
    },
    "list_dir": {
        "call": list_dir,
        "schema": {
            "type": "function",
            "function": {
                "name": "list_dir",
                "description": "List files and subdirectories in a directory (absolute or relative to cwd)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string"}
                    },
                    "required": ["path"]
                }
            }
        }
    },
}

def run_tool(name, args):
    return TOOLS[name]["call"](args)

def get_api_response(messages, system_prompt) -> dict:
    full_messages = [{"role": "system", "content": system_prompt}] + messages
    request = urllib.request.Request(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
        data=json.dumps({
            "model": MODEL,
            "messages": full_messages,
            "max_tokens": 8192,
            "tools": [tool["schema"] for tool in TOOLS.values()],
        }).encode(),
    )
    if DEBUG >= 2: print(f"{DIM}{request.data=}{RESET}")
    response = urllib.request.urlopen(request)
    return json.loads(response.read())

def main():
    messages = []
    system_prompt = f"Concise coding assistant. cwd: {os.getcwd()}"

    print(f"{BOLD}navicode{RESET} | {DIM}{MODEL}{RESET} | {DIM}{os.getcwd()}{RESET}\n")

    while True:
        try:
            user_input = input(f"{BOLD}{BLUE}>{RESET} ").strip()
            if not user_input:
                continue
            messages.append({"role": "user", "content": user_input})

            while True:
                response = get_api_response(messages, system_prompt)
                if DEBUG >= 2: print(f"{DIM}{json.dumps(response, indent=2)}{RESET}")

                choices = response["choices"]
                assert len(choices) == 1
                if DEBUG >= 1: print(f"{DIM}{choices[0]['finish_reason']}{RESET}")

                message = choices[0]["message"]
                content = message["content"]
                if len(content):
                    print(f"{CYAN}{content}{RESET}")
                    messages.append({"role": "assistant", "content": content})

                tool_calls = message.get("tool_calls")
                if not tool_calls:
                    break
                assert len(tool_calls) == 1
                function = tool_calls[0]["function"]
                id = tool_calls[0]["id"]
                fname = function["name"]
                fargs = json.loads(function["arguments"])
                print(f"{DIM}Calling: {fname}({fargs}){RESET}")
                tool_result = run_tool(fname, fargs)
                messages.append({"role": "tool", "tool_call_id": id, "content": tool_result})

            print()
        except KeyboardInterrupt:
            break

if __name__ == "__main__":
    main()
