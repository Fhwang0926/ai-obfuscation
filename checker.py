import os
from groq import Groq
import openai
import re
import shutil
from dotenv import load_dotenv
load_dotenv()

# OpenAI API 키와 모델 설정
openai.api_key = os.getenv("OPENAI_API_KEY")
openai_model = os.getenv("OPENAI_API_MODEL")

Groq.api_key = os.getenv("GROQ_API_KEY")
groq_model = os.getenv("GROQ_API_MODEL")

def get_all_files(directory):
    files_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            files_list.append(os.path.join(root, file))
    return files_list

def check_obfuscation(content_chunk, to="groq"):
    prompt = f"Is the following code obfuscated? Please answer with 'Yes' or 'No'.\n\n{content_chunk}"
    
    # openai
    response_text = ""
    if to == "openai":
        response = openai.ChatCompletion.create(
            model=openai_model,
            messages=[{"role": "user", "content": prompt}],
            # temperature=0  # 일관된 응답을 위한 설정
        )
        response_text = response.choices[0].message['content'].strip()
    elif to == "groq":
        # https://groq.com
        response = Groq().chat.completions.create(
            model=groq_model,
            messages=[{"role": "user", "content": prompt}],
        )
        
        response_text = response.choices[0].message.content.strip()

    return normalize_response(response_text)

def normalize_response(response):
    response_lower = response.lower()
    if "yes" in response_lower:
        return "Yes"
    elif "no" in response_lower:
        return "No"
    else:
        return "Uncertain"

def read_file_and_remove_comments(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            content_no_comments = remove_comments(content)
            return content_no_comments
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return None

def remove_comments(content):
    # 모든 주석 제거 (Python, JavaScript, Java, JSP, PHP, Ruby, Go, ASP, HTML, XML 등)
    content = re.sub(r'#.*', '', content)  # Python, Ruby 라인 주석
    content = re.sub(r'//.*', '', content)  # C, C++, Java, JavaScript, PHP, Go 라인 주석
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)  # C, C++, Java, JavaScript, PHP, Go 블록 주석
    content = re.sub(r'=begin.*?=end', '', content, flags=re.DOTALL)  # Ruby 블록 주석
    content = re.sub(r"'[^\n]*", '', content)  # ASP 라인 주석
    content = re.sub(r'<!--.*?-->', '', content, flags=re.DOTALL)  # HTML, XML 주석
    return content

def analyze_file_in_chunks(file_content, chunk_size=1000):
    chunks = [file_content[i:i + chunk_size] for i in range(0, len(file_content), chunk_size)]
    obfuscation_results = [check_obfuscation(chunk) for chunk in chunks]
    return obfuscation_results

def main(input_directory, output_directory):
    files_list = get_all_files(input_directory)
    
    if not os.path.exists(output_directory):
        os.makedirs(output_directory)
    
    obfuscation_results = {}
    
    for file in files_list:
        content_no_comments = read_file_and_remove_comments(file)
        if content_no_comments:
            if len(content_no_comments) < 1000:
                print(f"File {file} is smaller than 1000 bytes after removing comments. Skipping.")
                # continue
                obfuscation_checks = analyze_file_in_chunks(content_no_comments, len(content_no_comments))
            else:
                obfuscation_checks = analyze_file_in_chunks(content_no_comments, 1000)
            # Majority voting or any aggregation logic
            if obfuscation_checks.count("Yes") > obfuscation_checks.count("No"):
                final_result = "Yes"
            else:
                final_result = "No"
            print(f"chunk : {len(content_no_comments)}")  # 추가된 출력문
            obfuscation_results[file] = final_result
            
            # 파일 분류 및 복사
            if not os.path.exists(output_directory):
                os.makedirs(output_directory)
            
            if final_result == "Yes":
                result_subdir = os.path.join(output_directory, "obfuscated")
            elif final_result == "No":
                result_subdir = os.path.join(output_directory, "not_obfuscated")
            else:
                result_subdir = os.path.join(output_directory, "uncertain")
            
            if not os.path.exists(result_subdir):
                os.makedirs(result_subdir)
            
            shutil.copy(file, result_subdir)
    
    return obfuscation_results

# Example usage
input_directory = 'check'
output_directory = 'result'
results = main(input_directory, output_directory)

# Display the results
for file, obfuscation_check in results.items():
    print(f"File: {file}")
    print(f"  Obfuscation Check: {obfuscation_check}")
