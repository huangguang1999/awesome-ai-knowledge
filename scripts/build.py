#!/usr/bin/env python3
"""并发调 claude,把真实 AI 面试题批量生成「大白话」答案卡,按分类写入 docs/。
带缓存(scripts/.cache.json):已生成过的题不重复跑;首次运行会从现有 docs/ 回填缓存。
题源:datawhalechina/hello-agents、amitshekhariitbhu/ai-engineering-interview-questions。
"""
import concurrent.futures as cf
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache.json")
CLAUDE_BIN = os.path.expanduser("~/.local/bin/claude")
WORKERS = 6

H = "[datawhalechina/hello-agents](https://github.com/datawhalechina/hello-agents)"
A = "[amitshekhariitbhu/ai-engineering-interview-questions]" \
    "(https://github.com/amitshekhariitbhu/ai-engineering-interview-questions)"

# 分类key: (文件名, 标题, 一句话简介, 题源markdown)
CATS = {
    "LLM基础":   ("01-大模型基础.md", "大模型基础", "AI 是怎么读字、怎么生成、内部长什么样——入门先懂这些。", H),
    "Agent":     ("02-ai-agent.md", "AI Agent(智能体)", "让 AI 不止会聊天,还能自己规划、调工具、干完一件事。", H),
    "RAG":       ("03-rag.md", "RAG(检索增强)", "给 AI 配一个'随时能翻的资料库',让它少瞎编、能用上你自己的知识。", H),
    "评估":      ("04-评估.md", "模型与 Agent 评估", "怎么判断一个 AI / Agent 到底好不好用。", H),
    "Prompt":    ("05-prompt工程.md", "Prompt 工程", "同一个模型,会不会写提示词,效果天差地别。", A),
    "微调对齐":  ("06-微调与对齐.md", "微调与对齐", "怎么把通用大模型'调教'成你专属的、更听话的模型。", A),
    "工具MCP":   ("07-工具调用与mcp.md", "工具调用 & MCP", "让 AI 学会调 API、用工具,以及 MCP 这个'工具接口标准'。", A),
    "部署推理":  ("08-部署与推理优化.md", "部署与推理优化", "模型上线后怎么跑得更快、更省、更稳(LLMOps)。", A),
    "向量":      ("09-向量与embedding.md", "向量与 Embedding", "AI '理解语义'和'按相似度查找'的地基。", A),
    "多模态":    ("10-多模态.md", "多模态", "让 AI 不只看文字,还能看图、看视频、听声音。", f"{H} & {A}"),
    "应用安全":  ("11-应用实战与安全.md", "AI 应用实战 & 安全", "真把 AI 用到生产里会踩的坑,以及怎么防。", A),
}

# (分类key, 题目原文)——真实面试题,顺序即学习顺序
TOPICS = [
    # ===== 01 大模型基础(题源 hello-agents)=====
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

    # ===== 02 AI Agent(题源 hello-agents)=====
    ("Agent", "你如何定义一个基于 LLM 的智能体(Agent)?它通常由哪些核心组件构成?"),
    ("Agent", "请详细解释 ReAct 框架。它是如何将思维链和行动结合起来,以完成复杂任务的?"),
    ("Agent", "在 Agent 设计中规划能力很重要。目前有哪些主流方法可以赋予 LLM 规划能力?(例如 CoT、ToT、GoT)"),
    ("Agent", "Memory 是 Agent 的关键模块。如何为 Agent 设计短期记忆和长期记忆系统?可以借助哪些外部工具或技术?"),
    ("Agent", "Tool Use 是扩展 Agent 能力的有效途径。请从 Function Calling 角度解释 LLM 是如何学会调用外部 API 或工具的?"),
    ("Agent", "请比较 LangChain 和 LlamaIndex 这两个流行的 Agent 开发框架。它们的核心应用场景有何不同?"),
    ("Agent", "什么是多智能体系统?让多个 LLM Agent 协同工作相比单个 Agent 有什么优势?又会引入哪些新的复杂性?"),
    ("Agent", "在构建一个复杂的 Agent 时,你认为最主要的挑战是什么?"),
    ("Agent", "如何确保一个 Agent 的行为是安全、可控且符合人类意图的?在 Agent 设计中有哪些保障对齐的方法?"),

    # ===== 03 RAG(题源 hello-agents)=====
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

    # ===== 04 评估(题源 hello-agents)=====
    ("评估", "为什么传统的 NLP 评估指标(如 BLEU、ROUGE)对于评估现代 LLM 的生成质量存在很大局限性?"),
    ("评估", "请介绍几个目前行业内广泛使用的 LLM 综合性基准测试,并说明各自侧重点。(例如 MMLU、Big-Bench、HumanEval)"),
    ("评估", "什么是'LLM-as-a-Judge'?用 LLM 来评估另一个 LLM 的输出,有哪些优点和潜在的偏见?"),
    ("评估", "评估一个 Agent 为什么比评估一个基础 LLM 更加困难和复杂?评估的维度有哪些不同?"),

    # ===== 05 Prompt 工程(题源 ai-engineering-interview-questions)=====
    ("Prompt", "什么是 Prompt 工程(提示工程)?为什么它对 AI 应用如此关键?"),
    ("Prompt", "请用例子解释 zero-shot、one-shot 和 few-shot 提示。"),
    ("Prompt", "什么是自洽性(self-consistency)提示?它是如何提升模型推理能力的?"),
    ("Prompt", "什么是系统提示(system prompt)?它如何影响模型的行为?"),
    ("Prompt", "如何设计提示,让模型稳定地输出结构化结果(如 JSON、XML)?"),
    ("Prompt", "什么是提示注入(prompt injection)攻击?如何防御?"),
    ("Prompt", "什么是越狱(jailbreaking)?常见的越狱手法有哪些?"),
    ("Prompt", "如何针对成本和延迟来优化提示词?"),
    ("Prompt", "提示工程(prompt engineering)和提示微调(prompt tuning)有什么区别?"),
    ("Prompt", "什么是提示模板(prompt template)?生产环境里该怎么设计它?"),
    ("Prompt", "什么是角色提示(role prompting)?它在什么情况下最有效?"),

    # ===== 06 微调与对齐(题源 ai-engineering-interview-questions)=====
    ("微调对齐", "什么是微调(fine-tuning)?什么时候应该对一个 LLM 进行微调?"),
    ("微调对齐", "全量微调和参数高效微调(PEFT)有什么区别?"),
    ("微调对齐", "什么是 LoRA(低秩适配)?它是怎么工作的?"),
    ("微调对齐", "什么是 QLoRA?它是如何让消费级显卡也能微调大模型的?"),
    ("微调对齐", "什么是指令微调(instruction tuning)?为什么它对聊天模型很重要?"),
    ("微调对齐", "什么是灾难性遗忘(catastrophic forgetting)?微调时如何避免?"),
    ("微调对齐", "如何准备一份用于微调 LLM 的数据集?"),
    ("微调对齐", "什么是 RLHF(基于人类反馈的强化学习)?它是如何用来对齐 LLM 的?"),
    ("微调对齐", "什么是 DPO(直接偏好优化)?它和 RLHF / PPO 有什么不同?"),
    ("微调对齐", "什么是合成数据(synthetic data)?在微调中怎么用?"),
    ("微调对齐", "微调、RAG、提示工程三者到底该怎么选?"),

    # ===== 07 工具调用 & MCP(题源 ai-engineering-interview-questions)=====
    ("工具MCP", "什么是 Model Context Protocol(MCP)?它是如何标准化工具接入的?"),
    ("工具MCP", "如何为一个 AI Agent 设计和定义工具(tools)?"),
    ("工具MCP", "什么是 AI SubAgents(子智能体)?什么时候该拆出一个子 Agent?"),
    ("工具MCP", "LLM 选对了工具,却把参数传错了,如何修复参数提取?"),
    ("工具MCP", "Agent 工具很多却总挑错工具,如何提升工具选择的准确性?"),
    ("工具MCP", "什么是 Agent 循环(agent loop)?它是如何决定何时停止的?"),
    ("工具MCP", "如何在长流程 Agent 工作流里控制 token 消耗和成本?"),
    ("工具MCP", "什么是 Plan-and-Execute(先规划后执行)的 Agent 模式?"),

    # ===== 08 部署与推理优化(题源 ai-engineering-interview-questions)=====
    ("部署推理", "什么是 KV cache?它是如何加速推理的?"),
    ("部署推理", "什么是模型量化(quantization)?它如何减小模型体积、加速推理?"),
    ("部署推理", "什么是 Flash Attention?它解决了什么问题?"),
    ("部署推理", "大模型推理又慢又贵,有哪些优化延迟和吞吐的常见手段?"),
    ("部署推理", "什么是流式输出(streaming)?为什么 AI 的回答是一个字一个字往外蹦的?"),
    ("部署推理", "你的 LLM 回答太啰嗦,如何控制输出长度?"),
    ("部署推理", "如何让 LLM 学会说'我不知道',而不是硬编一个答案?"),
    ("部署推理", "处理长文档时撞到了模型的上下文窗口上限,如何应对?"),
    ("部署推理", "什么是 LLMOps?LLM 应用上线后如何监控、应对性能衰退?"),
    ("部署推理", "什么是模型蒸馏(distillation)?大模型是怎么'教'小模型的?"),
    ("部署推理", "什么是小语言模型(SLM)和大推理模型(LRM)?它们分别适合什么场景?"),

    # ===== 09 向量与 Embedding(题源 ai-engineering-interview-questions)=====
    ("向量", "什么是 embedding(向量)?模型是怎么把文字变成一串数字的?"),
    ("向量", "稀疏向量(sparse)和稠密向量(dense)有什么区别?"),
    ("向量", "余弦相似度、点积、欧氏距离在向量检索里分别怎么用?怎么选?"),
    ("向量", "什么是向量数据库?它和传统数据库有什么不同?"),
    ("向量", "向量维度(dimensionality)如何影响检索性能和成本?"),
    ("向量", "当 embedding 模型升级后出现'向量漂移'(embedding drift),该如何处理?"),
    ("向量", "什么是多模态 embedding?它是怎么生成的?"),
    ("向量", "什么是混合检索(hybrid search)?为什么它常常比纯向量检索更好?"),

    # ===== 10 多模态(题源 hello-agents VLM & ai-engineering-interview-questions)=====
    ("多模态", "Transformer 本来是处理文本的,它也能理解图像吗?多模态是怎么回事?"),
    ("多模态", "什么是视觉语言模型(VLM)?它和纯文本 LLM 有什么不同?"),
    ("多模态", "请解释 CLIP 模型的工作原理。它是如何通过对比学习把图像和文本'对齐'的?"),
    ("多模态", "扩散模型(Diffusion,如 Stable Diffusion、DALL·E)生成图像的基本原理是什么?"),
    ("多模态", "一个只处理文本的 RAG / Agent 系统,现在需要处理图片和表格,如何扩展?"),
    ("多模态", "多模态大模型的核心挑战是什么?即如何实现视觉和语言等不同模态信息的有效对齐和融合?"),

    # ===== 11 AI 应用实战 & 安全(题源 ai-engineering-interview-questions)=====
    ("应用安全", "什么是幻觉?如果 RAG 系统已经检索到了正确上下文却还在幻觉,该怎么修?"),
    ("应用安全", "如何给 AI Agent 加护栏(guardrails),防止它做出有害操作?"),
    ("应用安全", "什么是人在回路(human-in-the-loop)模式?什么时候需要它?"),
    ("应用安全", "AI Agent 可能执行不可逆操作(比如误删生产数据库),如何防范?"),
    ("应用安全", "如何用沙箱(sandbox)安全地运行一个会执行代码的 Agent?"),
    ("应用安全", "聊天机器人聊了十几轮后就丢失上下文,如何维持长对话?"),
    ("应用安全", "什么是查询改写(query transformation,如 HyDE、查询分解、step-back)?它如何提升检索?"),
    ("应用安全", "RAG 如何实现引用和来源标注(citation),让答案可追溯?"),
    ("应用安全", "LLM 可能把训练数据里的隐私/专有信息泄露出来,如何防止?"),
    ("应用安全", "包含业务逻辑的系统提示被用户套出来了,如何防止系统提示泄露?"),
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


def seed_from_docs():
    """首次运行无缓存时,从现有 docs/*.md 回填已生成的卡,避免重复跑。"""
    cache = {}
    if not os.path.isdir(DOCS):
        return cache
    for fn in os.listdir(DOCS):
        if not fn.endswith(".md"):
            continue
        text = open(os.path.join(DOCS, fn), encoding="utf-8").read()
        for sec in text.split("\n## ")[1:]:
            head, _, rest = sec.partition("\n")
            q = re.sub(r"^\d+\.\s*", "", head).strip()
            body = rest.split("\n---")[0].strip()
            if q and body and "生成失败" not in body:
                cache[q] = body
    return cache


def main():
    cache = {}
    if os.path.exists(CACHE):
        cache = json.load(open(CACHE, encoding="utf-8"))
    else:
        cache = seed_from_docs()
        print(f"从现有 docs 回填缓存: {len(cache)} 题")

    todo = [(c, q) for c, q in TOPICS if q not in cache]
    print(f"待生成: {len(todo)} 题(复用缓存 {len(TOPICS) - len(todo)} 题)")

    if todo:
        with cf.ThreadPoolExecutor(max_workers=WORKERS) as ex:
            fut = {ex.submit(gen, q): q for _, q in todo}
            done = 0
            for f in cf.as_completed(fut):
                q = fut[f]
                res = f.result()
                if res:
                    cache[q] = res
                done += 1
                print(f"[{done}/{len(todo)}] {'ok ' if res else 'FAIL'} {q[:34]}…", flush=True)
        json.dump(cache, open(CACHE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    n_total = 0
    for catkey, (fn, title, intro, src) in CATS.items():
        qs = [q for c, q in TOPICS if c == catkey]
        if not qs:
            continue
        lines = [f"# {title}\n", f"> {intro}\n",
                 f"> 题目出自 {src};答案为 AI 辅助生成的大白话版,使用前请自行核对。\n",
                 "[← 返回首页](../README.md)\n"]
        for i, q in enumerate(qs, 1):
            body = cache.get(q) or "_(生成失败,待补)_"
            lines.append(f"\n## {i}. {q}\n\n{body}\n\n---")
        open(os.path.join(DOCS, fn), "w", encoding="utf-8").write(
            "\n".join(lines).rstrip() + "\n")
        print(f"written {fn} ({len(qs)} 题)")
        n_total += len(qs)

    ok = sum(1 for _, q in TOPICS if cache.get(q))
    print(f"\n完成: 共 {n_total} 题,其中 {ok} 题有内容")


if __name__ == "__main__":
    main()
