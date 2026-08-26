# ARC Don't Tap The White Tile Plugin v0.0.3
[![Codacy Grade](https://app.codacy.com/project/badge/Grade/5a63d2a6d0b74c9d9d05d98b7acd581b)](https://app.codacy.com/gh/DEVILENMO/EndstoneMC-Dont-Tap-The-White-Tile-Plugin/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)
[![Version](https://img.shields.io/badge/version-v0.0.3-blue)](https://github.com/ARC-Minecraft/EndstoneMC-Dont-Tap-The-White-Tile-Plugin)


[English](#English) | [中文](#中文)

<div align="center">
    <img src="./demo.gif" alt="Game Demo">
    <p><em>Gameplay Demonstration / 游戏演示</em></p>
</div>

# English

## Introduction
ARC Don't Tap The White Tile is a classic mini-game plugin for Minecraft Bedrock servers. Players need to quickly tap black tiles to clear rows. The faster you clear them, the better ranking you'll get based on your completion time.

## Features
- Classic Don't Tap White Tile gameplay with 30-second time limit
- Custom configurations
- Multi-language support (Chinese/English)
- Player records and rankings system
- **Daily Check-in Rewards**: Get money rewards for first daily completion
- **Ranking Rewards**: Top 3 record breakers receive special money rewards
- **Economy Integration**: Compatible with arc_core and umoney plugins
- **Smart Timeout System**: Games automatically end after 30 seconds

## Installation
1. Place the plugin file in your server's plugins folder
2. Use /reload command in server
3. Configuration files will be automatically generated in `[server_root]/plugins/ARCDTWT/`

## Configuration
### Files Structure
- `DTWTConfig.yml`: Main configuration file
- `DTWTdata.db`: Database file for storing player records
- `ZH-CN.txt`: Chinese language file
- `ENG.txt`: English language file (optional, you can find in ./dist/ENG.txt)

### DTWTConfig.yml Parameters
```yaml
DEFAULT_LANGUAGE_CODE=ZH-CN  # Language setting (ZH-CN/ENG)
DATABASE_PATH=DTWTdata.db    # Database file path
TOTAL_BLACK_TILE_NUM=20      # Total rows to clear in each game
DAILY_REWARD_AMOUNT=500      # Daily first completion reward amount
FIRST_PLACE_REWARD=10000     # 1st place record breaking reward
SECOND_PLACE_REWARD=5000     # 2nd place record breaking reward
THIRD_PLACE_REWARD=2500      # 3rd place record breaking reward
```

### Commands
- `/dtwt` : View plugin description, rankings and personal records
- `/createdtwt` : Create a new game facility (OP only)

### Creating Game Facility
1. Build a 4×5×1 rectangle screen in the overworld
2. Place an easily breakable block (e.g., yellow wool) nearby as game trigger
3. Type /createdtwt
4. Follow the prompts to:
- Right-click the bottom-left corner of the screen
- Right-click the top-right corner
- Right-click the trigger block
5. A hint message will be shown white when setup is complete
6. Break the trigger block to start playing

### Reward System
- **Daily Rewards**: Players get money rewards for their first daily completion
- **Ranking Rewards**: Breaking into top 3 rankings grants special money rewards
- **Economy Requirements**: Requires arc_core or umoney plugin for money rewards
- **Game Timeout**: Each game has a 30-second time limit

# 中文

## 简介
ARC别踩白块是一个经典的Minecraft基岩版服务器小游戏插件。玩家需要快速点击黑色方块来消除行，完成速度越快，根据用时排名就越高。

## 特性
- 经典别踩白块玩法，30秒超时限制
- 自定义配置选项
- 多语言支持（中文/英文）
- 玩家记录与排名系统
- **每日打卡奖励**：每日首次完成可获得金钱奖励
- **破纪录奖励**：前三名破纪录者可获得特殊金钱奖励
- **经济插件集成**：兼容arc_core和umoney经济插件
- **智能超时系统**：游戏30秒后自动结束

## 安装
1. 将插件文件放入服务器插件文件夹
2. 启动/重启服务器
3. 配置文件将自动生成在`[服务器根目录]/plugins/ARCDTWT/`下

## 配置

### 文件结构
- `DTWTConfig.yml`: 主配置文件
- `DTWTdata.db`: 储存玩家记录的数据库文件
- `ZH-CN.txt`: 中文语言文件
- `ENG.txt`: 英文语言文件（可选）

### DTWTConfig.yml 参数说明
```yaml
DEFAULT_LANGUAGE_CODE=ZH-CN  # 语言设置（ZH-CN/ENG）
DATABASE_PATH=DTWTdata.db    # 数据库文件路径
TOTAL_BLACK_TILE_NUM=20      # 每局游戏需要消除的总行数
DAILY_REWARD_AMOUNT=500      # 每日首次完成奖励金额
FIRST_PLACE_REWARD=10000     # 第一名破纪录奖励
SECOND_PLACE_REWARD=5000     # 第二名破纪录奖励
THIRD_PLACE_REWARD=2500      # 第三名破纪录奖励
```

### 命令
- /dtwt: 查看插件说明、排行榜和个人记录
- /createdtwt: 创建新的游戏设施（仅OP可用）

### 创建游戏设施
1. 在主世界建造一个4×5×1的矩形屏幕
2. 在附近放置一个容易打碎的方块（如金色羊毛）作为触发器
3. 输入/createdtwt
4. 按提示依次：
- 右键点击屏幕左下角
- 右键点击屏幕右上角
- 右键点击触发方块
5. 设置完成后会有提示
6. 打碎触发方块即可开始游戏

### 奖励系统
- **每日奖励**：玩家每日首次完成游戏可获得金钱奖励
- **排名奖励**：打破前三名纪录可获得特殊金钱奖励
- **经济插件要求**：需要安装arc_core或umoney插件来发放金钱奖励
- **游戏超时**：每局游戏限时30秒

## 更新日志

### v0.0.3
- **修复群聊推送**：对接 `arc_qq_sync_astrbot`（AstrBot 弧光消息中枢），优先 `api_send_raw`
- **减少刷屏**：挑战失败不再全服广播、不再推送到 QQ 群（通关仍广播）
