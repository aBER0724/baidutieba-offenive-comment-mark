from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import sys
import requests
import re
from bs4 import BeautifulSoup
import time
from concurrent.futures import ThreadPoolExecutor
from bert_analyzer import BERTSentimentAnalyzer


max_page = 1
threads_num = 16

headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36"
}

cookies = {
    "BDUSS":""
}

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 实例化分析器
analyzer = BERTSentimentAnalyzer()
# 检测缓存
detect_cache = {}

def get_public_ip():
    try:
        response = requests.get("https://api.ipify.org")
        ip_info = response.text
        return ip_info
    except requests.RequestException as e:
        print(f"Error fetching IP: {e}")
        return "None"

def test_net():
    print("Network Testing...")
    print("出口ip: " + get_public_ip())
    
    response = requests.get("https://tieba.baidu.com/f?kw=%E5%AD%99%E7%AC%91%E5%B7%9D",headers=headers, stream=True, allow_redirects=False)
    response.encoding = 'utf-8' #设置编码格式
    soup = BeautifulSoup(response.text,'lxml')
    return True if soup.title.string != "百度安全验证"  and response.status_code == 200 else False

# 模拟等待
def time_down(seconds, random = True):
    # print("start wait=====")
    time.sleep(0.5 * seconds)
    # print("\nTime's up!=====")

# 检测是否 offensive
def detect_offensive(comment):
    if comment in detect_cache:
        return detect_cache[comment]
    
    result = json.loads(analyzer.insert(comment))
    detect_cache[comment] = result
    return result

# 采集帖子评论详情
def spider_tieba_detail(link, max_page = -1, repeat_count = 5):
    # 获取评论页面
    condition = False  # 初始条件
    first_run = True   # 标志变量
    results = []  # 用于存储每页评论的检测结果

    while (first_run or condition) and repeat_count > 0:
        try:
            response = requests.get(link, headers=headers, stream=True)
            response.encoding = 'utf-8'  # 设置编码格式
            soup = BeautifulSoup(response.text, 'lxml')
            
            if soup.title.string == '百度安全验证' or response.status_code != 200:
                condition = True 
                repeat_count = 0
            else: 
                condition = False
                repeat_count -= 1
        except requests.RequestException as e:  # 捕捉 requests 请求的异常
            print(f"Request failed: {e}")  # 打印错误信息
            condition = True  # 设置条件为 True 以退出循环
            
        first_run = False 
        
    if repeat_count == 0: return results  # 如果重复次数为0，返回空结果
    
    # 提取评论内容
    reply_list = [div.text.strip() for div in soup.select('div.d_post_content.j_d_post_content')]
    reply_list = [reply.strip() for reply in reply_list if reply.strip() != '']
    
    # 立即检测每页的评论
    for comment in reply_list:
        result = detect_offensive(comment)
        results.append(result)  # 将检测结果添加到结果列表中
        # 处理检测结果
        print(f"Detected result for comment: {result}")

    page_text = [a.text for a in soup.select('li.l_pager.pager_theme_5.pb_list_pager > a')]
    page_index = [a['href'] for a in soup.select('li.l_pager.pager_theme_5.pb_list_pager > a')]
    
    cur_page = [span.text for span in soup.select('li.l_pager.pager_theme_5.pb_list_pager > span')]
    cur_page = int(cur_page[0]) if cur_page else 1
    
    next_index = len(page_index) - 2

    end_page = 0
    next_url = ''
    
    if page_text:
        if page_text[len(page_text) - 1] == "尾页":
            end_page = int(int(re.search(r'pn=(\d+)', page_index[len(page_index) - 1]).group(1)) / 2)
            if max_page == -1:
                max_page = end_page
        next_url = 'https://tieba.baidu.com' + page_index[next_index]
    else:
        end_page = cur_page

    # print(f'{cur_page}/{max_page}')
    
    if next_url and cur_page < max_page:
        time_down(1, False)  # 等待, 避免触发安全验证
        results.extend(spider_tieba_detail(next_url, max_page))  # 递归调用并合并结果

    return results  # 返回所有检测结果

# 检测帖子
def detect_tweet(tweet_link, max_page = -1):
    result_list = spider_tieba_detail(tweet_link, max_page)  # 获取检测结果
    
    result = 0
    if result_list:
        for re in result_list:
            result += re["prob"]
        result = result / len(result_list)
        # print(result)
        return result
    else:
        return -1
    

class RequestHandler(BaseHTTPRequestHandler):
    # 支持 OPTIONS 请求以处理 CORS
    def do_OPTIONS(self):
        
        # 设置 CORS 头
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_POST(self):
        # 设置响应头
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        # 获取请求数据
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        tweets = json.loads(post_data)
        print("Received POST data:", tweets)
        
        flag = test_net()
        tweets_tags = [-1 for _ in range(len(tweets))]
        if flag:
            with ThreadPoolExecutor(max_workers=threads_num) as executor:
                # 使用 map 保持顺序
                tweets_tags = list(executor.map(lambda tweet: detect_tweet(tweet, max_page), tweets))
                print(f"Progress: {len(tweets_tags)}/{len(tweets)} tweets processed.")
                
        if all(tag == -1 for tag in tweets_tags):
            response = {"status": "failed", "results": tweets_tags}
        else:
            response = {"status": "success", "results": tweets_tags}

        # 返回响应
        print(json.dumps(response).encode('utf-8'))
        self.wfile.write(json.dumps(response).encode('utf-8'))
        
        if not flag :
            print("=======> Need Security Check <=======")
            print("| Please try again after changed IP.|")
            print("=====================================")
            httpd.server_close()

# 启动服务器
if test_net():
    print("-> Security Check Passed <-")
    server_address = ('', 13278)
    httpd = HTTPServer(server_address, RequestHandler)
    print("Server running on http://localhost:13278")
    httpd.serve_forever()
else:
    print("=======> Need Security Check <=======")
    print("| Please try again after changed IP.|")
    print("=====================================")