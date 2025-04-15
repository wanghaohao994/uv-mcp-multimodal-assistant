import json
import re
from typing import Dict, List, Any, Optional
from mcp.server.fastmcp import FastMCP

# 初始化 MCP 服务器
mcp = FastMCP("MarketServer")

# 模拟超市商品数据库
# 格式: {商品名: {品牌, 价格, 货架位置, 库存等信息}}
MARKET_DB = {
    "可乐": [
        {
            "id": "cola001",
            "name": "可口可乐",
            "brand": "可口可乐",
            "price": 3.5,
            "size": "330ml",
            "location": "A区3号货架第2排靠右侧",
            "stock": 48,
            "discount": False,
            "category": "饮料"
        },
        {
            "id": "cola002",
            "name": "百事可乐",
            "brand": "百事",
            "price": 3.0,
            "size": "330ml",
            "location": "A区3号货架第2排靠左侧",
            "stock": 36,
            "discount": True,
            "category": "饮料"
        },
        {
            "id": "cola003",
            "name": "零度可口可乐",
            "brand": "可口可乐",
            "price": 3.5,
            "size": "330ml",
            "location": "A区3号货架第3排中间",
            "stock": 24,
            "discount": False,
            "category": "饮料"
        }
    ],
    "矿泉水": [
        {
            "id": "water001",
            "name": "农夫山泉",
            "brand": "农夫山泉",
            "price": 2.0,
            "size": "550ml",
            "location": "A区2号货架第1排靠左侧",
            "stock": 120,
            "discount": False,
            "category": "饮料"
        },
        {
            "id": "water002",
            "name": "康师傅矿泉水",
            "brand": "康师傅",
            "price": 1.5,
            "size": "550ml",
            "location": "A区2号货架第1排靠右侧",
            "stock": 86,
            "discount": False,
            "category": "饮料"
        }
    ],
    "薯片": [
        {
            "id": "chips001",
            "name": "乐事原味薯片",
            "brand": "乐事",
            "price": 6.5,
            "size": "104g",
            "location": "B区1号货架第3排靠右侧",
            "stock": 32,
            "discount": False,
            "category": "零食"
        },
        {
            "id": "chips002",
            "name": "乐事番茄味薯片",
            "brand": "乐事",
            "price": 6.5,
            "size": "104g",
            "location": "B区1号货架第3排中间",
            "stock": 28,
            "discount": True,
            "category": "零食"
        },
        {
            "id": "chips003",
            "name": "旺旺小小酥",
            "brand": "旺旺",
            "price": 8.5,
            "size": "160g",
            "location": "B区1号货架第4排靠左侧",
            "stock": 45,
            "discount": False,
            "category": "零食"
        }
    ],
    "牛奶": [
        {
            "id": "milk001",
            "name": "蒙牛纯牛奶",
            "brand": "蒙牛",
            "price": 12.5,
            "size": "250ml*6",
            "location": "C区5号货架第1排冷藏区",
            "stock": 58,
            "discount": False,
            "category": "乳制品"
        },
        {
            "id": "milk002",
            "name": "伊利纯牛奶",
            "brand": "伊利",
            "price": 13.5,
            "size": "250ml*6",
            "location": "C区5号货架第2排冷藏区",
            "stock": 62,
            "discount": True,
            "category": "乳制品"
        }
    ],
    "方便面": [
        {
            "id": "noodle001",
            "name": "康师傅红烧牛肉面",
            "brand": "康师傅",
            "price": 4.5,
            "size": "单包",
            "location": "B区4号货架第1排靠左侧",
            "stock": 86,
            "discount": False,
            "category": "方便食品"
        },
        {
            "id": "noodle002",
            "name": "统一老坛酸菜牛肉面",
            "brand": "统一",
            "price": 4.8,
            "size": "单包",
            "location": "B区4号货架第1排靠右侧",
            "stock": 53,
            "discount": False,
            "category": "方便食品"
        }
    ],
    "宠物": [
        {
            "id": "dog001",
            "name": "焦糖狗",
            "brand": "泰迪",
            "price": 88,
            "size": "单只",
            "location": "A区6号货架第2排靠右侧",
            "stock": 1,
            "discount": False,
            "category": "狗"
        },
    ],
}

# 同义词字典
SYNONYMS = {
    "可乐": ["可乐", "Cola", "汽水"],
    "矿泉水": ["矿泉水", "纯净水", "饮用水", "瓶装水"],
    "薯片": ["薯片", "薯条", "膨化食品"],
    "牛奶": ["牛奶", "纯牛奶", "牛乳"],
    "方便面": ["方便面", "泡面", "速食面", "快餐面", "杯面"],
    "宠物": ["宠物", "狗", "猫", "宠物狗", "宠物猫","狗狗","猫猫"]
}

def search_product(query: str) -> List[Dict]:
    """
    根据用户输入的查询词搜索商品
    
    :param query: 用户输入的查询词
    :return: 匹配的商品列表
    """
    # 标准化查询词
    query = query.lower().strip()
    
    # 尝试从查询中提取商品名
    found_products = []
    
    # 检查是否直接匹配商品名
    for product_name, products in MARKET_DB.items():
        # 检查主商品名
        if product_name in query:
            found_products.extend(products)
            continue
            
        # 检查同义词
        if product_name in SYNONYMS:
            for synonym in SYNONYMS[product_name]:
                if synonym in query:
                    found_products.extend(products)
                    break
    
    return found_products

def format_product_results(products: List[Dict]) -> str:
    """
    将商品信息格式化为易读文本
    
    :param products: 商品信息列表
    :return: 格式化后的商品信息字符串
    """
    if not products:
        return "❌ 抱歉，没有找到您想要的商品。请尝试其他关键词或询问服务人员。"
    
    result = f"🛒 找到 {len(products)} 个相关商品:\n\n"
    
    for i, product in enumerate(products, 1):
        name = product.get("name", "未知商品")
        brand = product.get("brand", "")
        price = product.get("price", 0)
        size = product.get("size", "")
        location = product.get("location", "位置未知")
        stock = product.get("stock", 0)
        discount = "是" if product.get("discount", False) else "否"
        
        result += (
            f"{i}. 🏷️ {name} ({brand})\n"
            f"   💰 价格: ¥{price:.2f} / {size}\n"
            f"   📍 位置: {location}\n"
            f"   🗃️ 库存: {stock}件\n"
            f"   🔖 优惠: {discount}\n\n"
        )
    
    # 添加友好提示
    result += "需要帮助寻找商品吗？您可以前往服务台咨询，或者告诉我您需要的其他商品。"
    
    return result

@mcp.tool()
def find_product(query: str) -> str:
    """
    根据用户输入查询超市中的商品
    
    :param query: 用户输入的查询词，如"我想买可乐"、"在哪里能找到薯片"等
    :return: 格式化后的商品信息
    """
    products = search_product(query)
    return format_product_results(products)

@mcp.tool()
def list_category(category: str) -> str:
    """
    列出指定类别的所有商品
    
    :param category: 商品类别，如"饮料"、"零食"、"乳制品"等
    :return: 该类别下的所有商品信息
    """
    found_products = []
    
    for products in MARKET_DB.values():
        for product in products:
            if product.get("category", "").lower() == category.lower():
                found_products.append(product)
    
    return format_product_results(found_products)

if __name__ == "__main__":
    mcp.run(transport='stdio') 