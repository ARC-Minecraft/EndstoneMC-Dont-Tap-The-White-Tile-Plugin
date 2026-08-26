import os
from pathlib import Path

MAIN_PATH = 'plugins/ARCDTWT'

class LanguageManager:
    language_dict = {}  # Class variable shared across instances

    # 中文默认语言文件内容
    ZH_CN_CONTENT = {
        'DTWT_DESCRIPTION': '[弧光·别踩白块]别踩白块是一个趣味十足的小游戏，玩家需要快速点击黑色方块，每当点击一个黑色方块时，其所在的整行会被清除。游戏的目标是尽快完成消除{0}行黑色方块。插件内置计时功能，用于记录玩家完成任务的用时长短，最终根据时间排名决出最快的玩家！\\n排行榜：\\n1.{1}\\n2.{2}\\n3.{3}\\n你的最佳纪录：\\n用时：{4}\\n排名：{5}',
        'DTWT_HAS_ANOTHER_CREATOR_MESSAGE': '[弧光·别踩白块]有其他玩家({0})正在配置小游戏，请等待其完成后再试！',
        'DTWT_CREATE_HINT1': '[弧光·别踩白块]开始配置别踩白块小游戏，请点击作为小游戏显示屏左下角的起点方块！',
        'DTWT_CREATE_DISPLAYER_START_CORNER_SET_MESSAGE': '[弧光·别踩白块]起点方块配置成功，坐标：维度{0}',
        'DTWT_CREATE_HINT2': '[弧光·别踩白块]请点击作为小游戏显示屏右上角的终点方块！',
        'DTWT_CREATE_DISPLAYER_END_CORNER_SET_MESSAGE': '[弧光·别踩白块]终点方块配置成功，坐标：{0}',
        'DTWT_CREATE_HINT3': '[弧光·别踩白块]请点击作为游戏启动方块的启动方块！',
        'DTWT_CREATE_DISPLAYER_START_BLOCK_SET_MESSAGE': '[弧光·别踩白块]启动方块配置成功，坐标：{0}',
        'DTWT_CREATE_HINT4': '[弧光·别踩白块]别踩方块小游戏配置完毕！打碎启动方块即可开始游戏~',
        'DTWT_CREATE_COMPLETED_BROADCAST': '[弧光·别踩白块]别踩白块小游戏配置完毕，快来主世界维度{0}坐标位置参与挑战吧~',
        'DTWT_CREATE_WRONG_DISPLAYER_WIDTH_MESSAGE': '[弧光·别踩白块]你选择的显示屏宽度不为4，仅支持4x5尺寸的显示屏！',
        'DTWT_CREATE_WRONG_DISPLAYER_HEIGHT_MESSAGE': '[弧光·别踩白块]你选择的显示屏高度不为5，仅支持4x5尺寸的显示屏！',
        'DTWT_CREATE_DISPLAYER_NOT_A_PLANE_ERROR_MESSAGE': '[弧光·别踩白块]显示屏需要是一个竖着的平面！',
        'DTWT_CREATE_WRONG_DIMENSION_MESSAGE': '[弧光·别踩白块]游戏设置只支持布置在主世界维度，暂不支持{0}维度',
        'DTWT_GAME_START_BROADCAST': '[弧光·别踩白块]玩家{0}正在游玩别踩白块小游戏~快来围观呀~',
        'DTWT_GAME_START_HINT': '[弧光·别踩白块]游戏开始！加油破纪录！',
        'DTWT_GAME_ALREADY_STARTED_MESSAGE': '[弧光·别踩白块]玩家{0}正在游戏中，请等待游戏结束再开始！',
        'DTWT_PLAYER_CLICKED_INVALID_SCREEN_POS_MESSAGE': '[弧光·别踩白块]您正处于别踩白块小游戏中，请点击游戏设施屏幕位置！',
        'DTWT_PLAYER_CLICKED_WRONG_ROW_MESSGAE': '[弧光·别踩白块]请点击最下方那一行的黑色方块！',
        'DTWT_PLAYER_GAME_OVER_BROADCAST': '[弧光·别踩白块]玩家{0}游戏失败了，大家千万不要嘲笑他哟~',
        'DTWT_PLAYER_WIN_BROADCAST': '[弧光·别踩白块]玩家{0}成功通关别踩白块小游戏，用时{1}秒，个人最佳纪录{2}秒，最佳排名为~第{3}名！',
        'DTWT_GAME_TIMEOUT_MESSAGE': '[弧光·别踩白块]游戏超时！时间限制为30秒，挑战失败！',
        'DTWT_DAILY_REWARD_MESSAGE': '[弧光·别踩白块]恭喜获得每日首次完成奖励：{0}元！',
        'DTWT_RANK_REWARD_MESSAGE': '[弧光·别踩白块]恭喜你突破了第{0}名的排行记录，获得了奖金{1}元！',
        'DTWT_ECONOMY_NOT_AVAILABLE': '[弧光·别踩白块]经济系统不可用，无法发放奖金。'
    }

    def __init__(self, default_language_code):
        self.language_code = default_language_code.upper()
        if self.language_code not in LanguageManager.language_dict:
            LanguageManager.language_dict[self.language_code] = {}

        # 使用Path处理路径
        self.language_file_path = Path(MAIN_PATH) / f"{self.language_code}.txt"
        # 确保配置目录存在
        self.language_file_path.parent.mkdir(parents=True, exist_ok=True)
        # 如果是首次运行，创建中文语言文件
        self._create_default_zh_cn_file()
        # 加载语言文件
        self._load_language_file()

    def _create_default_zh_cn_file(self):
        """创建默认的中文语言文件"""
        zh_cn_path = Path(MAIN_PATH) / "ZH-CN.txt"

        # 如果中文语言文件不存在，创建它
        if not zh_cn_path.exists():
            with zh_cn_path.open("w", encoding="utf-8") as f:
                for key, value in self.ZH_CN_CONTENT.items():
                    f.write(f"{key}={value}\n")

    def _load_language_file(self):
        # Create config directory if not exists
        self.language_file_path.parent.mkdir(exist_ok=True)

        # Create language file if not exists
        if not self.language_file_path.exists():
            self.language_file_path.touch()

        # Load language file content
        with self.language_file_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and "=" in line:
                    key, value = line.split("=", 1)
                    LanguageManager.language_dict[self.language_code][key.strip()] = value.strip()

    def GetText(self, key, lang_code=None):
        # If no language code provided, use instance's language code
        target_lang = (lang_code or self.language_code).upper()

        # If the target language hasn't been loaded yet, load it
        if target_lang not in LanguageManager.language_dict:
            temp_manager = LanguageManager(target_lang)

        # If key doesn't exist in target language, add it
        if key not in LanguageManager.language_dict[target_lang]:
            target_file_path = Path(MAIN_PATH) / f"{target_lang}.txt"
            with target_file_path.open("a", encoding="utf-8") as f:
                f.write(f"\n{key}=")
            LanguageManager.language_dict[target_lang][key] = ""

        if not LanguageManager.language_dict[target_lang][key]:
            print(f'[ARCDTWT] Key {key} not found in language file {target_lang}.txt.')
            return ''
        else:
            return LanguageManager.language_dict[target_lang][key]