# awesome-ai-knowledge

> **AI 面试八股,但讲成人话。** 真实高频面试题 + 零基础也能看懂的大白话讲解。

满地都是给"标准答案"的面试题库,可对一个刚入门的人,那些答案本身就是另一道题:
满屏术语、堆公式、默认你已经懂。

这个仓库只做一件事:**把真实的 AI 面试题,讲到没有任何机器学习基础的人也能听懂。**
每道题都配一个生活化的比方、把每个术语顺手解释清楚——先让你"懂",再谈"会答"。

---

## 这适合谁

- 刚入门 AI / 想"会用 AI"、但被一堆术语劝退的人
- 转行、跨专业,想快速建立对大模型/Agent/RAG 的直觉
- 面试前想用大白话把八股"再过一遍"的人

如果你已经是算法老手、想要严谨推导和论文细节,这里可能太"浅"——那类资源已经很多,见文末「延伸阅读」。

## 目录

| 分类 | 题量 | 内容 |
|---|---|---|
| [大模型基础](docs/01-大模型基础.md) | 12 | 分词、注意力、位置编码、解码策略、MoE、涌现能力… |
| [AI Agent(智能体)](docs/02-ai-agent.md) | 9 | Agent 组件、ReAct、规划、记忆、工具调用、多智能体… |
| [RAG(检索增强)](docs/03-rag.md) | 10 | 工作原理、切块、Embedding、重排、Lost in the Middle… |
| [模型与 Agent 评估](docs/04-评估.md) | 4 | BLEU 局限、MMLU/HumanEval、LLM-as-a-Judge… |

> 持续扩充中。想看哪类题、或哪道讲得不够清楚,欢迎提 Issue。

## 每道卡长这样

每题固定四段,5 分钟看完:

- **💡 一句话先懂** — 先把核心用最朴素的话说清楚
- **🌰 打个比方** — 一个生活化类比,建立直觉
- **🔑 答题要点** — 面试真正该答的核心,术语随手解释
- **🚀 再进一步** — 想深入时的下一个线索

<details>
<summary>点开看一个真实例子(什么是词元化 / tokenization)</summary>

**💡 一句话先懂** 大模型其实不认识"字",它只认识数字。词元化就是在把文字喂给模型前,先把一句话切成一小块一小块(叫 token),再给每块编号……

**🌰 打个比方** 想象你玩乐高:不会为每栋房子单独开模具(按整词切),也不会全拆成塑料颗粒(按字母切),而是准备一套常用积木块(子词)——遇到没见过的新词,用这些块拼就行……

</details>

## 题目来源 & 致谢

- 面试题目主要整理自开源题库 **[datawhalechina/hello-agents](https://github.com/datawhalechina/hello-agents)**(Datawhale 出品),都是真实高频面试题。
- 感谢这些优秀的进阶题库:[wdndev/llm_interview_note](https://github.com/wdndev/llm_interview_note)、[WeThinkIn/AIGC-Interview-Book](https://github.com/WeThinkIn/AIGC-Interview-Book)。

## 内容是怎么生成的(透明说明)

每道题的大白话讲解由 **AI(Claude)辅助生成**,再按统一的"零基础"标准组织。
我们尽量保证准确,但 **AI 可能出错,尤其是非常具体的工具/版本细节**——
请把它当作"快速建立理解"的入门读物,关键内容建议再对照官方文档核实。
发现错误?直接提 Issue / PR,这正是开源协作的意义。

## 贡献

非常欢迎:
- 🐛 **纠错**:哪句讲错了、比方不恰当,提 Issue 或 PR
- ➕ **加题**:补充真实面试遇到的题(请注明出处),或认领目录里还没覆盖的方向
- ✍️ **改写**:把某道题讲得更通俗、比方更贴切

加题请沿用四段结构(💡🌰🔑🚀),保持"讲人话"的风格。

## Roadmap

- [ ] 扩到 100+ 题(补充 Prompt 工程、Function Calling、MCP、多模态等方向)
- [ ] 每道题加"面试官可能追问"
- [ ] 配套**每日一题推送 bot**(已有原型:飞书/邮件/Telegram 自托管,每天推一题到你私聊)

## 延伸阅读(更进阶 / 更全)

- [wdndev/llm_interview_note](https://github.com/wdndev/llm_interview_note) — 大模型面试笔记(全面)
- [小林coding AI 面试题](https://xiaolincoding.com/other/ai.html) — 530+ 题含答案
- [datawhalechina/hello-agents](https://github.com/datawhalechina/hello-agents) — Agent 教程 + 面试总结

## License

[MIT](LICENSE) — 内容可自由使用,注明出处即可。
