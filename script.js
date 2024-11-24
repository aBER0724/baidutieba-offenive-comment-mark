// ==UserScript==
// @name         baidutieba-offenive-comment-mark
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  为网页每个帖子添加标签
// @author       aBER
// @match        https://tieba.baidu.com/f?kw=*
// @match        https://c.tieba.baidu.com/f?kw=*
// @grant        GM_xmlhttpRequest
// @connect      example.com
// ==/UserScript==

(function () {
  "use strict";

  async function send_message(method, url, data = {}) {
    return new Promise((resolve, reject) => {
      GM_xmlhttpRequest({
        method: method,
        url: url,
        headers: {
          "Content-Type": "application/json",
        },
        data: JSON.stringify(data),
        setTimeout: 30000,
        ontimeout: function () {
          console.error("服务器返回超时");
          reject(new Error("请求超时")); // Reject with timeout error
        },
        onload: function (response) {
          try {
            // 解析 JSON 响应
            const jsonResponse = JSON.parse(response.responseText);
            console.log(jsonResponse.status);

            // 处理响应数据
            if (jsonResponse.status === "success") {
              resolve(jsonResponse.results); // 使用 resolve 返回结果
            } else {
              console.error("Error in response:", jsonResponse);
              reject(new Error("Response status not successful")); // 处理错误
            }
          } catch (error) {
            reject(error); // 解析 JSON 出错
          }
        },
        onerror: function (error) {
          console.error("Request failed:", error);
          reject(error); // 请求失败
        },
      });
    });
  }

  // 使用 async/await 等待结果
  async function getTags(URL, links) {
    let tags;
    const posts = document.querySelectorAll("div.threadlist_title a.j_th_tit");
    const tag_parent = document.querySelectorAll(
      "div.col2_right.j_threadlist_li_right"
    );

    // 在每个帖子下添加“正在检测中...”标签
    for (let i = 0; i < posts.length; i++) {
      const tagElement = document.createElement("div");
      tagElement.className = "post-tag";
      tagElement.style.textAlign = "center";
      tagElement.textContent = "正在检测中...";
      tag_parent[i].appendChild(tagElement); // 将标签插入到帖子元素内部
    }

    try {
      tags = await send_message("POST", URL, links);
      console.log("Tags results:", tags);

      // 更新标签内容
      for (let i = 0; i < posts.length; i++) {
        const tagElement = tag_parent[i].querySelector(".post-tag");
        if (tagElement) {
          let tag = parseFloat((tags[i] * 100).toFixed(1));
          tagElement.textContent = `Offensive ${tag}%`; // 更新标签内容
          // 根据不同的值设置不同的背景色
          if (tag === 0) {
            tagElement.style.backgroundColor = "#e6f3e6"; // 浅绿色
            tagElement.style.color = "#2e7d32";
          } else if (tag > 0 && tag <= 25) {
            tagElement.style.backgroundColor = "#fff9c4"; // 浅黄色
            tagElement.style.color = "#f57f17";
          } else if (tag > 25 && tag <= 50) {
            tagElement.style.backgroundColor = "#fff3e0"; // 浅橙色
            tagElement.style.color = "#e65100";
          } else if (tag > 50 && tag <= 75) {
            tagElement.style.backgroundColor = "#ffebee"; // 浅红色
            tagElement.style.color = "#c62828";
          } else if (tag > 75 && tag <= 100) {
            tagElement.style.backgroundColor = "#ffcdd2"; // 深红色
            tagElement.style.color = "#b71c1c";
          } else {
            tagElement.style.backgroundColor = "#f5f5f5"; // 灰色
            tagElement.style.color = "#616161";
          }
        }
      }
    } catch (error) {
      console.error("Failed to fetch tags:", error);
      // 更新标签为错误信息
      for (let i = 0; i < posts.length; i++) {
        const tagElement = tag_parent[i].querySelector(".post-tag");
        if (tagElement) {
          tagElement.textContent = "检测失败, 服务器更换 IP 后重试"; // 更新为错误信息
          tagElement.style.backgroundColor = "#ffccbc"; // 设置背景色为浅红色
          tagElement.style.color = "#c62828"; // 设置字体颜色为深红色
        }
      }
    }
  }

  function get_posts_tag() {
    const posts = document.querySelectorAll("div.threadlist_title a.j_th_tit");
    const links = Array.from(posts).map((post) => post.href);
    const SEVER_URL = "https://dexample.com";

    getTags(SEVER_URL, links);
  }

  window.onload = function () {
    get_posts_tag();
  };
})();
