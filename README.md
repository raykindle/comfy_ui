# 持续解读 ComfyUI 官方源码

[ComfyUI 官方源码](https://github.com/comfyanonymous/ComfyUI)

当你踏入 ComfyUI 的世界，你仿佛穿越进了未来的绘图板，这不仅是一个项目，更是一次前所未有的体验！

在这个无限可能的舞台上，你将感受到代码的魔力，它不仅能够开启你的想象力，还能引领你进入技术的深渊。ComfyUI 不仅仅是一个工具，它是一座通往创造力巅峰的桥梁。

随着项目的不断演进，你将发现自己置身于一个充满活力和创新的社区中。这里没有局限，只有无限的可能性等待着你去探索。无论是解读源码，升级功能，还是定制专属插件，你都能找到属于自己的舞台。

加入我们，一起探索未知的领域，一起创造属于我们的未来！在 ComfyUI 的世界里，创意无处不在，未来由你定义！
<br>
<br/>

### 📝 &nbsp; 未来计划
- [ ] &nbsp; [梳理解读解释路线](zestful_note/interpret_route.md) 
- [ ] &nbsp; 零门槛上手 ComfyUI
- [ ] &nbsp; 绘制项目流程图
- [ ] &nbsp; 手把手教你部署 ComfyUI 的多并发 API 服务
- [ ] &nbsp; 手把手教你定制专属自己的 ComfyUI 插件
- [ ] &nbsp; 研究基于ComfyUI开发的AIGC产品的商业化落地
<br>
<br/>

### 🔍 &nbsp; 项目流程图
敬请期待
<br>
<br/>

### ⏳ &nbsp; 解读进度
每个 **目录 / 文件** 尾部，若出现 ✅，代表 **已解读**
```
~/comfy_ui
├── app
├── comfy
│   ├── cldm
│   ├── extra_samplers
│   ├── k_diffusion
│   ├── ldm
│   │   ├── cascade
│   │   ├── models
│   │   └── modules
│   │       ├── diffusionmodules
│   │       ├── distributions
│   │       └── encoders
│   ├── sd1_tokenizer
│   ├── t2i_adapter
│   └── taesd
├── comfy_extras
│   └── chainner_models
│       └── architecture
│           ├── OmniSR
│           ├── face
│           └── timm
├── custom_nodes
├── input
├── models
│   ├── checkpoints
│   ├── clip
│   ├── clip_vision
│   ├── configs
│   ├── controlnet
│   ├── diffusers
│   ├── embeddings
│   ├── gligen
│   ├── hypernetworks
│   ├── loras
│   ├── photomaker
│   ├── style_models
│   ├── unet
│   ├── upscale_models
│   ├── vae
│   └── vae_approx
├── notebooks
├── output
├── script_examples
├── tests
│   ├── compare
│   └── inference
│       └── graphs
├── tests-ui
│   ├── tests
│   └── utils
├── web
│   ├── extensions
│   │   └── core                        # 前端源码
│   ├── lib
│   ├── scripts
│   │   └── ui
│   └── types
├── CHANGELOG.md
├── README.md
├── cuda_malloc.py
├── execution.py
├── extra_model_paths.yaml.example
├── folder_paths.py
├── latent_preview.py
├── main.py                             # 程序主入口 ✅
├── new_updater.py
├── node_helpers.py
├── nodes.py
├── pytest.ini
├── requirements.txt
└── server.py
```
<br>
<br/>

### 🫡 &nbsp; 加入我们 🍻
#### ComfyUI 开发者微信交流群
<img alt="ComfyUI 开发者微信交流群" referrerPolicy="no-referrer" src="https://i0.hdslb.com/bfs/article/d436591005cc4718f10885bafdb75dc8321621609.jpg@256w_256h_1e.jpg"/>

#### 作者微信
<img alt="作者微信" referrerPolicy="no-referrer" src="https://i0.hdslb.com/bfs/article/f8f88877954fb04994bebf92f8b4af46321621609.jpg@256w_256h_1e.jpg"/>

#### [Discord](https://discord.gg/unmDfHTe)
<br>
<br/>