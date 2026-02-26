import requests
import datetime
import json
import os
from dotenv import load_dotenv  # 新增：加载环境变量
import lunardate  # 导入农历处理库

# 加载环境变量
load_dotenv()

# ====== 从环境变量获取配置 ======
APP_ID = os.getenv("APP_ID")
APP_SECRET = os.getenv("APP_SECRET")
OPEN_ID = os.getenv("OPEN_ID")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
TEMPLATE_ID = os.getenv("TEMPLATE_ID")
CITY = os.getenv("CITY", "永州")

# 婷婷的农历生日（格式：年-月-日，仅月/日生效）
TINGTING_LUNAR_BIRTHDAY = os.getenv("TINGTING_LUNAR_BIRTHDAY", "2002-09-22")
# 恋爱纪念日（阳历，格式：年-月-日）
LOVE_START_DATE = os.getenv("LOVE_START_DATE", "2025-05-20")
# 新增：你们认识的日期（阳历，格式：年-月-日）
MEET_START_DATE = os.getenv("MEET_START_DATE", "2025-03-17")

# ================================

def get_access_token():
    """获取微信接口调用凭证"""
    url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APP_ID}&secret={APP_SECRET}"
    try:
        response = requests.get(url, timeout=10).json()
        if "access_token" in response:
            return response["access_token"]
        else:
            raise Exception(f"获取access_token失败: {response}")
    except Exception as e:
        raise Exception(f"请求微信接口异常: {str(e)}")

def get_weather():
    """从心知天气API获取真实天气数据"""
    if not WEATHER_API_KEY:
        raise Exception("未配置心知天气API Key")

    url = f"https://api.seniverse.com/v3/weather/daily.json?key={WEATHER_API_KEY}&location={CITY}&language=zh-Hans&unit=c&start=0&days=1"

    try:
        response = requests.get(url, timeout=10).json()
        if "results" in response and len(response["results"]) > 0:
            weather_data = response["results"][0]["daily"][0]
            return {
                "weather": weather_data["text_day"],
                "temp_min": weather_data["low"],
                "temp_max": weather_data["high"],
                "wind": weather_data["wind_direction"],
                "wind_scale": weather_data["wind_scale"]
            }
        else:
            raise Exception(f"心知天气返回异常: {response}")
    except Exception as e:
        raise Exception(f"获取天气失败: {str(e)}")

def calculate_special_days():
    """计算农历生日、恋爱天数、认识天数"""
    today = datetime.datetime.now().date()

    # 1. 计算距离婷婷农历生日的天数
    lunar_birth = datetime.datetime.strptime(TINGTING_LUNAR_BIRTHDAY, "%Y-%m-%d")
    lunar_birth_month = lunar_birth.month
    lunar_birth_day = lunar_birth.day

    lunar_this_year = lunardate.LunarDate(today.year, lunar_birth_month, lunar_birth_day, 0)
    solar_birth_this_year = lunar_this_year.toSolarDate()
    solar_birth_this_year = datetime.date(
        solar_birth_this_year.year,
        solar_birth_this_year.month,
        solar_birth_this_year.day
    )

    if solar_birth_this_year < today:
        lunar_next_year = lunardate.LunarDate(today.year + 1, lunar_birth_month, lunar_birth_day, 0)
        solar_birth_this_year = lunar_next_year.toSolarDate()
        solar_birth_this_year = datetime.date(
            solar_birth_this_year.year,
            solar_birth_this_year.month,
            solar_birth_this_year.day
        )

    birthday_days_left = (solar_birth_this_year - today).days

    # 2. 计算恋爱的天数（阳历）
    love_start = datetime.datetime.strptime(LOVE_START_DATE, "%Y-%m-%d").date()
    love_days = (today - love_start).days

    # 3. 新增：计算认识的天数（阳历）
    meet_start = datetime.datetime.strptime(MEET_START_DATE, "%Y-%m-%d").date()
    meet_days = (today - meet_start).days

    return {
        "birthday_days": birthday_days_left,
        "love_days": love_days,
        "meet_days": meet_days  # 新增：认识天数
    }

def get_daily_message():
    """生成每日推送内容（新增认识天数）"""
    today = datetime.datetime.now().strftime("%Y年%m月%d日")
    weather = get_weather()
    special_days = calculate_special_days()

    # 早安/晚安切换逻辑
    hour = datetime.datetime.now().hour
    if 6 <= hour < 12:
        greeting = "早安呀宝贝 💖"
        extra_msg = f"今天{weather['weather']}，温度{weather['temp_min']}°C-{weather['temp_max']}°C，{weather['wind']}{weather['wind_scale']}级，记得好好吃早餐～"
    elif 20 <= hour < 24:
        greeting = "晚安呀宝贝 😘"
        extra_msg = f"今天{weather['weather']}，温度{weather['temp_min']}°C-{weather['temp_max']}°C，早点休息，不许熬夜～"
    else:
        greeting = "想你啦宝贝 🥰"
        extra_msg = f"当前天气{weather['weather']}，温度{weather['temp_min']}°C-{weather['temp_max']}°C，记得照顾好自己～"

    return {
        "date": today,
        "location": CITY,
        "weather": f"{weather['weather']} {weather['temp_min']}°C-{weather['temp_max']}°C（{weather['wind']}{weather['wind_scale']}级）",
        "birthday_days": special_days["birthday_days"],
        "love_days": special_days["love_days"],
        "meet_days": special_days["meet_days"],  # 新增：认识天数
        "extra_msg": extra_msg,
        "greeting": greeting
    }

def send_wechat_message(access_token, data):
    """发送微信模板消息（新增认识天数字段）"""
    url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"

    payload = {
        "touser": OPEN_ID,
        "template_id": TEMPLATE_ID,
        "data": {
            "date": {"value": data["date"], "color": "#FF69B4"},
            "location": {"value": data["location"], "color": "#32CD32"},
            "weather": {"value": data["weather"], "color": "#1E90FF"},
            "birthday_days": {"value": data["birthday_days"], "color": "#FF4500"},
            "love_days": {"value": data["love_days"], "color": "#FF1493"},
            "meet_days": {"value": data["meet_days"], "color": "#9932CC"},  # 新增：认识天数（紫蓝色）
            "extra_msg": {"value": data["extra_msg"], "color": "#FF8C00"},
            "greeting": {"value": data["greeting"], "color": "#FF1493"},
            "footer": {"value": "来自你的专属小管家 💌", "color": "#9370DB"}
        }
    }

    try:
        headers = {"Content-Type": "application/json; charset=utf-8"}
        response = requests.post(url, data=json.dumps(payload, ensure_ascii=False).encode('utf-8'), headers=headers,
                                 timeout=10)
        result = response.json()
        if result.get("errcode") == 0:
            return {"success": True, "msg": "推送成功"}
        else:
            raise Exception(f"微信推送失败: {result}")
    except Exception as e:
        raise Exception(f"发送消息异常: {str(e)}")

if __name__ == "__main__":
    try:
        # 验证必填配置
        required_configs = ["APP_ID", "APP_SECRET", "OPEN_ID", "WEATHER_API_KEY", "TEMPLATE_ID"]
        missing = [cfg for cfg in required_configs if not os.getenv(cfg)]
        if missing:
            raise Exception(f"缺少必要配置: {', '.join(missing)}")

        # 验证lunardate库
        test_lunar = lunardate.LunarDate(2024, 8, 15, 0)
        print(f"农历库测试成功：2024年农历八月十五 → 阳历 {test_lunar.toSolarDate()}")

        # 1. 获取access_token
        access_token = get_access_token()
        print(f"获取access_token成功: {access_token[:20]}...")

        # 2. 生成消息
        message_data = get_daily_message()
        print(f"生成消息内容: {message_data}")

        # 3. 发送消息
        result = send_wechat_message(access_token, message_data)
        print(result)

    except ImportError as e:
        print(f"导入错误：{e} → 请执行 pip install -r requirements.txt 安装依赖")
    except Exception as e:
        print(f"程序执行失败: {str(e)}")
        exit(1)