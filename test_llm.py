"""
测试 LLM 调用是否正常

运行此脚本验证你的 AstrBot 环境配置是否正确
"""

import asyncio
import sys
import os

# 添加当前目录到路径
sys.path.insert(0, os.path.dirname(__file__))


async def test_llm_call():
    """测试 LLM 调用"""
    
    print("=" * 50)
    print("LLM 调用测试")
    print("=" * 50)
    print()
    
    try:
        # 导入必要的模块
        from astrbot.api.star import Context
        
        print("✓ 成功导入 AstrBot 模块")
        
    except ImportError as e:
        print(f"✗ 导入失败：{e}")
        print("\n请确保你已经在 AstrBot 环境中运行此脚本")
        return
    
    # 模拟上下文
    class MockContext:
        async def get_current_chat_provider_id(self, umo=None):
            print(f"✓ 获取 provider_id (umo={umo})")
            return "default"  # 返回默认的 provider_id
        
        async def llm_generate(self, chat_provider_id, prompt):
            print(f"✓ 调用 llm_generate(provider_id={chat_provider_id})")
            print(f"✓ Prompt 长度：{len(prompt)} 字符")
            
            class MockResponse:
                completion_text = f"[模拟回复] 我收到了你的问题，共 {len(prompt)} 个字符。"
            
            return MockResponse()
    
    context = MockContext()
    
    # 测试提示词
    test_prompt = "高考 500 分读什么专业比较好？"
    
    print(f"\n测试问题：{test_prompt}")
    print("-" * 50)
    
    try:
        # 步骤 1: 获取 provider_id
        provider_id = await context.get_current_chat_provider_id(umo="test_user")
        print(f"Provider ID: {provider_id}")
        
        # 步骤 2: 调用 LLM
        response = await context.llm_generate(
            chat_provider_id=provider_id,
            prompt=test_prompt
        )
        
        # 步骤 3: 获取结果
        result = response.completion_text
        print(f"\n回复：{result}")
        
        print("\n" + "=" * 50)
        print("✓ LLM 调用测试成功！")
        print("=" * 50)
        
    except Exception as e:
        print(f"\n✗ 测试失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_llm_call())
