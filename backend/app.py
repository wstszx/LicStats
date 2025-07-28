import re
from flask import Flask, request, jsonify
from flask_cors import CORS
import io

app = Flask(__name__)
CORS(app)  # 允许跨域请求，方便前后端联调

# 用于匹配 "Users of <feature_name>:" 行
FEATURE_LINE_RE = re.compile(r"^\s*Users of ([\w.-]+):.*$")

# 用于匹配 "licenses issued" 和 "licenses in use" 行
ISSUED_IN_USE_RE = re.compile(r"^\s*\"(.*)\" licenses issued.*licenses in use:\s*(\d+).*$")

# 用于匹配每个用户的使用信息行
# username hostname display (v<version>) (<server>/<port> <handle>), start <Day> <M/D> <H:M>
USER_LINE_RE = re.compile(
    r"^\s*([^\s]+)\s+([^\s]+)\s+[^\s]+\s+\(v[\d.]+\)\s+\([^\s]+\/\d+\s+\d+\),\s+start\s+(.*)$"
)

def parse_lmstat_log(log_content):
    """
    解析lmstat日志文件的核心函数。
    """
    features = {}
    current_feature = None
    lines = log_content.splitlines()

    for line in lines:
        # 匹配功能模块名称
        feature_match = FEATURE_LINE_RE.match(line)
        if feature_match:
            feature_name = feature_match.group(1)
            current_feature = {
                "featureName": feature_name,
                "licensesIssued": 0,
                "licensesInUse": 0,
                "users": []
            }
            features[feature_name] = current_feature
            continue

        # 匹配许可证总数和在用数
        issued_in_use_match = ISSUED_IN_USE_RE.match(line)
        if issued_in_use_match and current_feature:
            # 注意：lmstat的输出中，issued数量可能在user list之后，所以我们找到就更新
            # 这里我们假设它在user list之前，如果之后再出现，会覆盖
            # 实际解析中，issued数量通常在feature声明的下一行
            # 为了简化，我们假设一个feature块内只有一个licenses issued行
            if current_feature["licensesIssued"] == 0: # 避免重复赋值
                 current_feature["licensesIssued"] = int(issued_in_use_match.group(2))
            continue


        # 匹配用户信息
        user_match = USER_LINE_RE.match(line)
        if user_match and current_feature:
            username = user_match.group(1)
            hostname = user_match.group(2)
            start_time = user_match.group(3)
            
            current_feature["users"].append({
                "username": username,
                "hostname": hostname,
                "startTime": start_time,
            })
            # 更新正在使用的许可证数量
            current_feature["licensesInUse"] = len(current_feature["users"])

    # 清理掉没有用户使用的feature（如果需要）
    # final_features = {k: v for k, v in features.items() if v['licensesInUse'] > 0}
    
    return list(features.values())

@app.route('/api/analyze', methods=['POST'])
def analyze_log():
    """
    API接口，接收上传的日志文件并返回分析结果。
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file:
        try:
            # 直接在内存中读取和解码文件内容
            log_content = file.read().decode('utf-8')
            
            # 调用解析函数
            analysis_result = parse_lmstat_log(log_content)
            
            return jsonify(analysis_result)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5001) # 使用一个不常用的端口以避免冲突