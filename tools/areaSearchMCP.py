import json
import httpx
import os
from typing import Any, Dict, Optional, List
from mcp.server.fastmcp import FastMCP

# 初始化 MCP 服务器
mcp = FastMCP("AreaSearchServer")

# 高德地图 API 配置
AMAP_API_BASE = "https://restapi.amap.com/v3/place/around"
API_KEY = os.getenv("AMAP_API_KEY")  # 从环境变量获取API密钥
USER_AGENT = "area-search-app/1.0"

# 商业楼固定位置坐标（经度,纬度）- 请替换为你的实际位置
DEFAULT_LOCATION = "29.349636,105.930739"  # 示例坐标，永川时代天街

async def fetch_poi_around(
    keyword: Optional[str] = None,
    types: Optional[str] = None,
    radius: int = 3000,
    location: str = DEFAULT_LOCATION,
    page: int = 1,
    offset: int = 10,
    extensions: str = "all"
) -> Dict[str, Any]:
    """
    从高德地图API获取周边POI信息
    
    :param keyword: 搜索关键词
    :param types: POI类型编码，多个类型用"|"分隔
    :param radius: 搜索半径，单位：米
    :param location: 中心点坐标，格式："经度,纬度"
    :param page: 页码
    :param offset: 每页记录数，最大25
    :param extensions: 返回结果详细程度：base/all
    :return: POI数据字典；若出错返回包含error信息的字典
    """
    params = {
        "key": API_KEY,
        "location": location,
        "radius": radius,
        "offset": offset,
        "page": page,
        "extensions": extensions,
        "sortrule": "distance"  # 按距离排序
    }
    
    # 添加可选参数
    if keyword:
        params["keywords"] = keyword
    if types:
        params["types"] = types
        
    headers = {"User-Agent": USER_AGENT}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(AMAP_API_BASE, params=params, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP 错误: {e.response.status_code}"}
        except Exception as e:
            return {"error": f"请求失败: {str(e)}"}

def format_poi_result(data: Dict[str, Any]) -> str:
    """
    将POI数据格式化为易读文本
    
    :param data: POI数据字典
    :return: 格式化后的POI信息字符串
    """
    if "error" in data:
        return f"⚠️ {data['error']}"
        
    if data.get("status") != "1":
        return f"⚠️ API请求错误: {data.get('info', '未知错误')}"
    
    pois = data.get("pois", [])
    if not pois:
        return "⚠️ 未找到符合条件的地点"
    
    result = f"🔍 找到 {len(pois)} 个地点:\n\n"
    
    for i, poi in enumerate(pois[:10], 1):  # 最多显示10个结果
        name = poi.get("name", "未知")
        address = poi.get("address", "地址未知")
        distance = poi.get("distance", "未知")
        tel = poi.get("tel", "暂无")
        type_info = poi.get("type", "")
        business_hours = poi.get("business_hours", "营业时间未知")
        rating = poi.get("biz_ext", {}).get("rating", "暂无") if "biz_ext" in poi else "暂无"
        
        result += (
            f"{i}. 📍 {name}\n"
            f"   📝 类型: {type_info}\n"
            f"   🏠 地址: {address}\n"
            f"   🚶 距离: {distance}米\n"
            f"   ☎️ 电话: {tel}\n"
            f"   ⏰ 营业: {business_hours}\n"
            f"   ⭐ 评分: {rating}\n\n"
        )
    
    return result

@mcp.tool()
async def search_nearby(
    keyword: Optional[str] = None,
    type_code: Optional[str] = None,
    radius: int = 3000
) -> str:
    """
    搜索商业楼周边的指定类型地点
    
    :param keyword: 搜索关键词，如"咖啡"、"餐厅"等
    :param type_code: 高德地图POI类型代码，如"050000"(餐饮)，"060000"(购物)等
    :param radius: 搜索半径，单位米，默认3000米
    :return: 格式化后的周边信息
    """
    data = await fetch_poi_around(keyword=keyword, types=type_code, radius=radius)
    return format_poi_result(data)

@mcp.tool()
async def search_nearby_food(radius: int = 2000) -> str:
    """
    搜索附近的餐饮场所
    
    :param radius: 搜索半径，单位米，默认2000米
    :return: 格式化后的餐饮信息
    """
    data = await fetch_poi_around(types="050000", radius=radius)
    return format_poi_result(data)

@mcp.tool()
async def search_nearby_shopping(radius: int = 2000) -> str:
    """
    搜索附近的购物场所
    
    :param radius: 搜索半径，单位米，默认2000米
    :return: 格式化后的购物信息
    """
    data = await fetch_poi_around(types="060000", radius=radius)
    return format_poi_result(data)

@mcp.tool()
async def search_nearby_entertainment(radius: int = 3000) -> str:
    """
    搜索附近的娱乐场所
    
    :param radius: 搜索半径，单位米，默认3000米
    :return: 格式化后的娱乐场所信息
    """
    data = await fetch_poi_around(types="080000", radius=radius)
    return format_poi_result(data)

if __name__ == "__main__":
    mcp.run(transport='stdio') 