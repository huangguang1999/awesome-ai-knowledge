#!/usr/bin/env python3
"""并发调 claude,把真实 AI 面试题批量生成「大白话」答案卡,按分类写入 docs/。
题目出自 datawhalechina/hello-agents(开源面试题库)。
"""
import concurrent.futures as cf
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
CLAUDE_BIN = os.path.expanduser("~/.local/bin/claude")
WORKERS = 5

# (分类key, 文件名, 标题, 一句话简介)
CATS = {
    "LLM基础": ("01-大模型基础.md", "大模型基础", "AI 是怎么读字、怎么生成、内部长什么样——入门先懂这些。"),
    "Agent":   ("02-ai-agent.md", "AI Agent(智能体)", "让 AI 不止会聊天,还能自己规划、调工具、干完一件事。"),
    "RAG":     ("03-rag.md", "RAG(检索增强)", "给 AI 配一个'随时能翻的资料库',让它少瞎编、能用上你自己的知识。"),
    "评估":    ("04-评估.md", "模型与 Agent 评估", "怎么判断一个 AI / Agent 到底好不好用。"),
}

# (分类key, 题目原文)——真实面试题,顺序即学习顺序
TOPICS = [
    ("LLM基础", "什么是词元化(tokenization)?请比较 BPE 和 WordPiece 这两种主流子词切分算法。"),
    ("LLM基础", "LLM 推理时有哪些常见的解码策略?请解释 Greedy Search、Beam Search、Top-K 采样和 Top-P(Nucleus)采样的原理和优缺点。"),
    ("LLM基础", "请解释 Transformer 中的自注意力机制是如何工作的?它为什么比 RNN 更适合处理长序列?"),
    ("LLM基础", "什么是位置编码?在 Transformer 中为什么它是必需的?请列举至少两种实现方式。"),
    ("LLM基础", "你觉得 NLP 和 LLM 最大的区别是什么?两者有何共同点和不同点?"),
    ("LLM基础", "请比较 Encoder-Only、Decoder-Only 和 Encoder-Decoder 三种架构,说明各自最擅长的任务类型。"),
    ("LLM基础", "怎么理解大模型的'涌现能力'?它通常在模型规模达到什么程度时出现?"),
    ("LLM基础", "LLM 常用的激活函数有哪些?为什么选用它?"),
    ("LLM基础", "什么是 Scaling Laws(规模定律)?它揭示了模型性能、计算量和数据量之间的什么关系?"),
    ("LLM基础", "你知道 MHA、MQA、GQA 的区别吗?请详细解释一下。"),
    ("LLM基础", "请详细介绍 RoPE(旋转位置编码),对比绝对位置编码,它的优劣势分别是什么?"),
    ("LLM基础", "混合专家模型(MoE)是如何在不显著增加推理成本的情况下,有效扩大模型参数规模的?请简述其工作原理。"),

    ("Agent", "你如何定义一个基于 LLM 的智能体(Agent)?它通常由哪些核心组件构成?"),
    ("Agent", "请详细解释 ReAct 框架。它是如何将思维链和行动结合起来,以完成复杂任务的?"),
    ("Agent", "在 Agent 设计中规划能力很重要。目前有哪些主流方法可以赋予 LLM 规划能力?(例如 CoT、ToT、GoT)"),
    ("Agent", "Memory 是 Agent 的关键模块。如何为 Agent 设计短期记忆和长期记忆系统?可以借助哪些外部工具或技术?"),
    ("Agent", "Tool Use 是扩展 Agent 能力的有效途径。请从 Function Calling 角度解释 LLM 是如何学会调用外部 API 或工具的?"),
    ("Agent", "请比较 LangChain 和 LlamaIndex 这两个流行的 Agent 开发框架。它们的核心应用场景有何不同?"),
    ("Agent", "什么是多智能体系统?让多个 LLM Agent 协同工作相比单个 Agent 有什么优势?又会引入哪些新的复杂性?"),
    ("Agent", "在构建一个复杂的 Agent 时,你认为最主要的挑战是什么?"),
    ("Agent", "如何确保一个 Agent 的行为是安全、可控且符合人类意图的?在 Agent 设计中有哪些保障对齐的方法?"),

    ("RAG", "请解释 RAG 的工作原理。与直接对 LLM 进行微调相比,RAG 主要解决了什么问题?有哪些优势?"),
    ("RAG", "一个完整的 RAG 流水线包含哪些关键步骤?请从数据准备到最终生成,详细描述整个过程。"),
    ("RAG", "在构建知识库时文本切块(chunking)策略至关重要。你会如何选择合适的切块大小和重叠长度?背后有什么权衡?"),
    ("RAG", "如何选择一个合适的嵌入(Embedding)模型?评估一个 Embedding 模型的好坏有哪些指标?"),
    ("RAG", "除了基础的向量检索,你还知道哪些可以提升 RAG 检索质量的技术?"),
    ("RAG", "请解释'Lost in the Middle'问题。它描述了 RAG 中的什么现象?有什么方法可以缓解?"),
    ("RAG", "如何全面地评估一个 RAG 系统的性能?请分别从检索和生成两个阶段提出评估指标。"),
    ("RAG", "了解搜索系统吗?它和 RAG 有什么区别?"),
    ("RAG", "传统 RAG 是'先检索后生成',你是否了解更复杂的 RAG 范式,比如在生成过程中多次检索或自适应检索?"),
    ("RAG", "在什么场景下,你会选择用图数据库或知识图谱来增强或替代传统的向量数据库检索?"),

    ("评估", "为什么传统的 NLP 评估指标(如 BLEU、ROUGE)对于评估现代 LLM 的生成质量存在很大局限性?"),
    ("评估", "请介绍几个目前行业内广泛使用的 LLM 综合性基准测试,并说明各自侧重点。(例如 MMLU、Big-Bench、HumanEval)"),
    ("评估", "什么是'LLM-as-a-Judge'?用 LLM 来评估另一个 LLM 的输出,有哪些优点和潜在的偏见?"),
    ("评估", "评估一个 Agent 为什么比评估一个基础 LLM 更加困难和复杂?评估的维度有哪些不同?"),
]

PROMPT = """你是一位耐心的 AI 启蒙老师,读者是**零基础的 AI 入门者**(想学会理解和使用 AI / 大模型 / agent,不是搞算法研究)。
下面是一道**真实的 AI 面试题**,请把它的答案讲成零基础也能懂的大白话。

面试题:{q}

要求:
- 假设读者没有任何机器学习背景,出现的术语都顺带用一句话解释清楚
- 多打生活化的比方、讲直觉,尽量不用公式;能联系"实际怎么用"就联系
- 准确、是真能在面试里说出口的要点,但表达通俗、鼓励

严格只输出下面四段 markdown(不要重复题目,不要任何开场白或客套,不要用代码块包住整体):

**💡 一句话先懂**
<2~4 句把核心说清楚>

**🌰 打个比方**
<一个生活化类比或具体小例子>

**🔑 答题要点**
<分 2~4 点,这就是面试该答的核心;每点一行,术语随手解释>

**🚀 再进一步**
<一个延伸小问题或"想深入可以了解 X",一句话>"""


def gen(q):
    try:
        r = subprocess.run([CLAUDE_BIN, "-p", PROMPT.format(q=q),
                            "--output-format", "text"],
                           capture_output=True, text=True, timeout=240,
                           env=dict(os.environ))
        out = r.stdout.strip()
        if r.returncode == 0 and len(out) >= 40:
            return out
        sys.stderr.write(f"[warn] rc={r.returncode} len={len(out)} q={q[:30]}\n")
    except subprocess.TimeoutExpired:
        sys.stderr.write(f"[warn] timeout q={q[:30]}\n")
    return None


def main():
    results = {}
    with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
        fut = {ex.submit(gen, q): (cat, q) for cat, q in TOPICS}
        done = 0
        for f in cf.as_completed(fut):
            cat, q = fut[f]
            results[(cat, q)] = f.result()
            done += 1
            print(f"[{done}/{len(TOPICS)}] {cat} :: {q[:34]}…", flush=True)

    SRC = "> 题目出自开源面试题库 [datawhalechina/hello-agents]" \
          "(https://github.com/datawhalechina/hello-agents);答案为 AI 辅助生成的大白话版,使用前请自行核对。"
    for catkey, (fn, title, intro) in CATS.items():
        lines = [f"# {title}\n", f"> {intro}\n", SRC, "\n[← 返回首页](../README.md)\n"]
        n = 0
        for cat, q in TOPICS:
            if cat != catkey:
                continue
            n += 1
            body = results.get((cat, q)) or "_(生成失败,待补)_"
            lines.append(f"\n## {n}. {q}\n\n{body}\n\n---")
        path = os.path.join(DOCS, fn)
        open(path, "w", encoding="utf-8").write("\n".join(lines).rstrip() + "\n")
        print(f"written {path} ({n} 题)")

    ok = sum(1 for v in results.values() if v)
    print(f"\n完成: {ok}/{len(TOPICS)} 题生成成功")


if __name__ == "__main__":
    main()
