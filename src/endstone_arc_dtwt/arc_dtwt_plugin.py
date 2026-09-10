import math
import random
import time
from datetime import datetime, date

from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from endstone import ColorFormat, Player
from endstone.command import Command, CommandSender
from endstone.event import event_handler, PlayerInteractEvent, BlockBreakEvent
from endstone.form import ActionForm
from endstone.plugin import Plugin

from endstone_arc_dtwt.DatabaseManager import DatabaseManager
from endstone_arc_dtwt.LanguageManager import LanguageManager
from endstone_arc_dtwt.SettingManager import SettingManager

MAIN_PATH = 'plugins/ARCDTWT'

class ARCDTWTPlugin(Plugin):
    api_version = "0.7"
    commands = {
        "dtwt":
            {
                "description": "Show description of 'ARC Don't Tap the White Tile' plugin.",
                "usages": ["/dtwt"],
                "permissions": ["arc_dtwt.command.dtwt"]
            },
        "createdtwt": 
            {
                "description": "Create a new game facility, will delete the old one if exists.",
                "usages": ["/createdtwt"],
                "permissions": ["arc_dtwt.command.createdtwt"]
            }
    }
    permissions = {
        "arc_dtwt.command.dtwt": {
            "description": "Can used by everyone.",
            "default": True
        },
        "arc_dtwt.command.createdtwt": {
            "description": "Can used by OP.",
            "default": "op"
        }
    }

    def __init__(self):
        super().__init__()
        self.setting_manager = SettingManager()
        default_language_dode = self.setting_manager.GetSetting('DEFAULT_LANGUAGE_CODE')
        self.language_manager = LanguageManager(default_language_dode if default_language_dode is not None else 'ZH-CN')
        # database
        self.db_manager = DatabaseManager(Path(MAIN_PATH) / self.setting_manager.GetSetting('DATABASE_PATH'))
        self._init_database()

        # Interact time record dict
        self.interact_time_dict = {}

        # Current Facility
        self.current_facility = self.get_game_facility()
        if self.current_facility is not None:
            # 在__init__中不能使用self.logger打印，因为self.logger还没有初始化
            print(f'[ARC DTWT]Successfully load game facility, game displayer ({self.current_facility['screen_start']} -> {self.current_facility['screen_end']}), start trigger at {self.current_facility['trigger_pos']}.')

        # Deploy new facility function
        self.if_in_deploying_state = False
        self.creator_name = None
        self.screen_start = None
        self.screen_end = None
        self.trigger_pos = None

        # Game function
        try:
            self.total_black_tile_num = int(self.setting_manager.GetSetting('TOTAL_BLACK_TILE_NUM'))
        except (ValueError, TypeError):
            self.total_black_tile_num = 20
        self.if_in_game = False
        self.game_start_time = None
        self.player_name = None
        self.current_display_seq = [None for _ in range(5)]
        self.current_black_tile_index = 0
        # Timeout check
        self.timeout_check_task = None
        
        # Reward settings
        try:
            self.daily_reward_amount = int(self.setting_manager.GetSetting('DAILY_REWARD_AMOUNT'))
        except (ValueError, TypeError):
            self.daily_reward_amount = 100
        try:
            self.first_place_reward = int(self.setting_manager.GetSetting('FIRST_PLACE_REWARD'))
        except (ValueError, TypeError):
            self.first_place_reward = 500
        try:
            self.second_place_reward = int(self.setting_manager.GetSetting('SECOND_PLACE_REWARD'))
        except (ValueError, TypeError):
            self.second_place_reward = 300
        try:
            self.third_place_reward = int(self.setting_manager.GetSetting('THIRD_PLACE_REWARD'))
        except (ValueError, TypeError):
            self.third_place_reward = 200
        
        self.economy_plugin = None

    def on_load(self) -> None:
        self.logger.info(f"{ColorFormat.YELLOW}[ARC DTWT]Plugin loaded!")

    def on_enable(self) -> None:
        self.register_events(self)

        # Initialize economy plugin - check arc_core first, then umoney
        try:
            self.economy_plugin = self.server.plugin_manager.get_plugin('arc_core')
            if self.economy_plugin is not None:
                print("[ARC DTWT]Using ARC Core economy system for money rewards.")
                self._register_arc_main_menu_button()
            else:
                self.economy_plugin = self.server.plugin_manager.get_plugin('umoney')
                if self.economy_plugin is not None:
                    print("[ARC DTWT]Using UMoney economy system for money rewards.")
                else:
                    print("[ARC DTWT]No supported economy plugin found (arc_core or umoney). Money rewards will not be available.")
        except Exception as e:
            print(f"[ARC DTWT]Failed to load economy plugin: {e}. Money rewards will not be available.")

        self.logger.info(f"{ColorFormat.YELLOW}[ARC DTWT]Plugin enabled!")

    def on_disable(self) -> None:
        try:
            core = self.server.plugin_manager.get_plugin("arc_core")
            if core is not None and hasattr(core, "api_unregister_main_menu_button"):
                core.api_unregister_main_menu_button("arc_dtwt:main")
        except Exception:
            pass
        self.logger.info(f"{ColorFormat.YELLOW}[ARC DTWT]Plugin disabled!")

    def _register_arc_main_menu_button(self) -> None:
        core = getattr(self, "economy_plugin", None)
        if core is None or not hasattr(core, "api_register_main_menu_button"):
            return
        try:
            core.api_register_main_menu_button(
                "arc_dtwt:main",
                "别踩白块小游戏",
                on_click=self.show_dtwt_panel,
                priority=6,
            )
        except Exception as e:
            print(f"[ARC DTWT]Failed to register ARC main menu button: {e}")

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        if command.name == "dtwt":
            if not isinstance(sender, Player):
                sender.send_message(f'[ARC DTWT]This command only works for players.')
                return True
            self.show_dtwt_panel(sender)
            return True
        if command.name == "createdtwt":
            if not isinstance(sender, Player):
                sender.send_message(f'[ARC DTWT]This command only works for players.')
                return True
            if not self.if_in_deploying_state or self.creator_name == sender.name:
                self.clear_deployment_memory()
                self.if_in_deploying_state = True
                self.creator_name = sender.name
                sender.send_message(self.language_manager.GetText('DTWT_CREATE_HINT1'))
            else:
                sender.send_message(self.language_manager.GetText('DTWT_HAS_ANOTHER_CREATOR_MESSAGE').format(self.creator_name))
            return True
        return False

    def show_dtwt_panel(self, player: Player):
        """显示DTWT游戏信息和排行榜面板"""
        # 获取前10个记录
        top_records = self.get_leaderboard(10)
        
        # 构建排行榜列表
        rank_list = []
        if len(top_records) > 0:
            for i, (player_name, best_time) in enumerate(top_records):
                rank_list.append(f"§6{i + 1}. §f{player_name} - §a{round(best_time, 3)}秒")
        else:
            rank_list.append("§7暂无记录")
        
        # 获取当前玩家的记录
        player_best_time = self.get_player_best_time(player.xuid)
        player_rank = self.get_player_rank(player.xuid)
        
        if player_best_time is None:
            player_record_text = "§c您还没有完成记录"
        else:
            player_record_text = f"§e您的最佳记录: §a{round(player_best_time, 3)}秒\n§e您的排名: §6第{player_rank if player_rank is not None else '∞'}名"
        
        # 构建面板内容
        content = f"§l§bARC 别踩白块游戏§r\n\n"
        content += f"§e游戏目标: §f点击 §6{self.total_black_tile_num} §f个黑色方块\n\n"
        content += f"§l§6=== 排行榜 TOP 10 ===§r\n"
        content += '\n'.join(rank_list) + '\n\n'
        content += f"§l§e=== 您的记录 ===§r\n"
        content += player_record_text
        
        # 创建面板
        dtwt_panel = ActionForm(
            title="§l§bARC 别踩白块",
            content=content
        )
        
        player.send_form(dtwt_panel)

    @event_handler
    def on_player_interact(self, event: PlayerInteractEvent):
        if self.if_in_deploying_state:
            if event.player.name == self.creator_name:
                if not self.check_if_valid_click(self.creator_name):
                    return
                if event.block is None:
                    return
                if event.block.dimension.name != 'Overworld':
                    event.player.send_message(self.language_manager.GetText('DTWT_CREATE_WRONG_DIMENSION_MESSAGE').format(event.block.dimension.name))
                    return
                if self.screen_start is None:
                    self.screen_start = (event.block.location.x, event.block.location.y, event.block.location.z)
                    event.player.send_message(self.language_manager.GetText('DTWT_CREATE_DISPLAYER_START_CORNER_SET_MESSAGE').format(self.screen_start))
                    event.player.send_message(self.language_manager.GetText('DTWT_CREATE_HINT2'))
                    return
                if self.screen_end is None:
                    possible_end_corner = (event.block.location.x, event.block.location.y, event.block.location.z)
                    # Judge if a 4 x 5 displayer
                    if self.screen_start[0] == possible_end_corner[0]:
                        # Width is supposed to be 4
                        if math.fabs(self.screen_start[2] - possible_end_corner[2]) != 3:
                            event.player.send_message(self.language_manager.GetText('DTWT_CREATE_WRONG_DISPLAYER_WIDTH_MESSAGE'))
                            return
                        # Height = 5?
                        if possible_end_corner[1] - self.screen_start[1] != 4:
                            event.player.send_message(self.language_manager.GetText('DTWT_CREATE_WRONG_DISPLAYER_HEIGHT_MESSAGE'))
                            return
                    elif self.screen_start[2] == possible_end_corner[2]:
                        # Width is supposed to be 4
                        if math.fabs(self.screen_start[0] - possible_end_corner[0]) != 3:
                            event.player.send_message(self.language_manager.GetText('DTWT_CREATE_WRONG_DISPLAYER_WIDTH_MESSAGE'))
                            return
                        # Height = 5?
                        if possible_end_corner[1] - self.screen_start[1] != 4:
                            event.player.send_message(self.language_manager.GetText('DTWT_CREATE_WRONG_DISPLAYER_HEIGHT_MESSAGE'))
                            return
                    else:
                        event.player.send_message(self.language_manager.GetText('DTWT_CREATE_DISPLAYER_NOT_A_PLANE_ERROR_MESSAGE'))
                        return
                    self.screen_end = possible_end_corner
                    # display green screen
                    # f'fill {' '.join([str(_) for _ in self.screen_start])} {' '.join([str(_) for _ in self.screen_end])} lime_wool'
                    self.server.dispatch_command(self.server.command_sender, self.get_fill_command(self.screen_start, self.screen_end, 'green_wool'))
                    event.player.send_message(self.language_manager.GetText('DTWT_CREATE_DISPLAYER_END_CORNER_SET_MESSAGE').format(self.screen_end))
                    event.player.send_message(self.language_manager.GetText('DTWT_CREATE_HINT3'))
                    return
                if self.trigger_pos is None:
                    self.trigger_pos = (event.block.location.x, event.block.location.y, event.block.location.z)
                    event.player.send_message(self.language_manager.GetText('DTWT_CREATE_DISPLAYER_START_BLOCK_SET_MESSAGE').format(self.trigger_pos))
                    s = self.update_game_facility(self.screen_start, self.screen_end, self.trigger_pos)
                    if not s:
                        self.logger.error(f'[ARC DTWT]An error occurred while saving game facility to database.')
                    else:
                        self.display_single_color('white')
                        event.player.send_message(self.language_manager.GetText('DTWT_CREATE_HINT4'))
                        self.server.broadcast_message(self.language_manager.GetText('DTWT_CREATE_COMPLETED_BROADCAST').format(self.trigger_pos))
                        self.current_facility = self.get_game_facility()
                    self.clear_deployment_memory()
                    return
            else:
                return
        if self.if_in_game and event.player.name == self.player_name:
            if not self.check_if_valid_click(self.creator_name):
                return
            if event.block is None:
                return
            # Update game
            screen_pos = self.convert_world_pos_to_screen_pos((event.block.location.x, event.block.location.y, event.block.location.z))
            if screen_pos is None:
                event.player.send_message(self.language_manager.GetText('DTWT_PLAYER_CLICKED_INVALID_SCREEN_POS_MESSAGE'))
                return
            if screen_pos[1] != 0:
                event.player.send_message(self.language_manager.GetText('DTWT_PLAYER_CLICKED_WRONG_ROW_MESSGAE'))
                return
            if screen_pos[0] == self.current_display_seq[0]:
                self.current_black_tile_index += 1
                if self.current_black_tile_index == self.total_black_tile_num:
                    self.end_game(True, event.player)
                    return
                new_seq = self.current_display_seq[1:]
                if self.current_black_tile_index + 5 > self.total_black_tile_num:
                    new_seq.append(None)
                else:
                    new_seq.append(random.randint(0, 3))
                self.displayer_game_update(new_seq)
            else:
                self.end_game(False, event.player)
            return
        return

    @staticmethod
    def _is_overworld_dimension(dimension_name: str) -> bool:
        """兼容 Dimension.name（Overworld）与规范 ID（minecraft:overworld）。"""
        raw = str(dimension_name or "").strip()
        if not raw:
            return False
        key = "".join(c for c in raw.lower() if c.isalnum() or c == ":")
        return key in ("overworld", "minecraft:overworld")

    def api_judge_if_start_block(self, x: float, y: float, z: float, dimension_name: str) -> bool:
        """
        判断指定坐标的方块是否为游戏开始方块
        :param x: 方块X坐标
        :param y: 方块Y坐标
        :param z: 方块Z坐标
        :param dimension_name: 维度名称（Overworld / overworld / minecraft:overworld 均可）
        :return: 是否为游戏开始方块
        """
        if self.current_facility is None or not self._is_overworld_dimension(dimension_name):
            return False

        trigger = self.current_facility["trigger_pos"]
        return (
            math.floor(x) == math.floor(trigger[0])
            and math.floor(y) == math.floor(trigger[1])
            and math.floor(z) == math.floor(trigger[2])
        )

    @event_handler
    def on_block_breaked(self, event: BlockBreakEvent):
        if self.current_facility is not None:
            if not self.if_in_game:
                if event.block is None:
                    return
                if self.api_judge_if_start_block(event.block.location.x, event.block.location.y, event.block.location.z, event.block.dimension.name):
                    self.start_game(event.player.name)
                    event.player.send_message(self.language_manager.GetText('DTWT_GAME_START_HINT'))
                    self.server.broadcast_message(self.language_manager.GetText('DTWT_GAME_START_BROADCAST').format(event.player.name))
                    event.is_cancelled = True
                    return
                return
            else:
                if event.block is None:
                    return
                if self.api_judge_if_start_block(event.block.location.x, event.block.location.y, event.block.location.z, event.block.dimension.name):
                    event.player.send_message(self.language_manager.GetText('DTWT_GAME_ALREADY_STARTED_MESSAGE').format(self.player_name))
                    event.is_cancelled = True
                    return
                return

    # Deploy
    def clear_deployment_memory(self):
        self.if_in_deploying_state = False
        self.creator_name = None
        self.screen_start = None
        self.screen_end = None
        self.trigger_pos = None

    # Game
    def start_game(self, player_name: str):
        self.if_in_game = True
        self.player_name = player_name
        self.game_start_time = time.time()

        # Set 30 seconds timeout
        self.timeout_check_task = self.server.scheduler.run_task(
            self,
            lambda: self.check_game_timeout(),
            delay=30 * 20  # 30秒后强制结束游戏（转换为游戏tick，1秒=20tick）
        )

        # Random generate first 5 rows
        start_seq = []
        for _ in range(5):
            seed = int(time.time()) + _
            rg = random.Random(seed)
            start_seq.append(rg.randint(0, 3))
        self.displayer_game_update(start_seq)

    def end_game(self, if_successful: bool, player: Player):
        if if_successful:
            # Set displayer color
            self.display_single_color('lime')
            # Update record and check for rewards
            time_cost = time.time() - self.game_start_time
            
            # Check daily reward before updating record
            can_get_daily_reward = self.can_receive_daily_reward(player.xuid)
            
            # Update player record
            update_success, is_new_record = self.update_player_record(player.xuid, player.name, time_cost)
            
            # Give daily reward if eligible
            if can_get_daily_reward:
                self.give_money_to_player(player, self.daily_reward_amount, "每日首次完成")
            
            # Check for rank reward if it's a new record
            if is_new_record:
                new_rank = self.get_player_rank(player.xuid)
                if new_rank is not None and new_rank <= 3:
                    self.check_and_give_rank_reward(player, new_rank)
            
            # Broadcast win only（失败不广播，避免刷屏）
            best_time = self.get_player_best_time(player.xuid)
            player_rank = self.get_player_rank(player.xuid)
            broadcast_message = self.language_manager.GetText('DTWT_PLAYER_WIN_BROADCAST').format(player.name,
                                                                                                            round(time_cost, 3),
                                                                                                            round(best_time, 3) if best_time is not None else '∞',
                                                                                                            player_rank if player_rank is not None else '∞')
            self.server.broadcast_message(broadcast_message)
            
            # Send to QQ group
            self.send_to_qq_group(broadcast_message)
        else:
            # Set displayer color；挑战失败仅改屏显色，不广播、不推群
            self.display_single_color('red')
        # clear game memory
        self.if_in_game = False
        self.player_name = None
        self.game_start_time = None
        self.current_display_seq = [None for _ in range(5)]
        self.current_black_tile_index = 0
        # Cancel timeout check task if exists
        if self.timeout_check_task is not None:
            try:
                self.timeout_check_task.cancel()
            except:
                pass
            self.timeout_check_task = None

    def check_game_timeout(self):
        """30秒超时强制结束游戏"""
        if not self.if_in_game or self.game_start_time is None:
            return
        
        # 30秒到了，强制结束游戏
        player = self.server.get_player(self.player_name)
        if player is not None:
            player.send_message(self.language_manager.GetText('DTWT_GAME_TIMEOUT_MESSAGE'))
            self.end_game(False, player)

    # Avoid interact jitter
    def check_if_valid_click(self, player_name: str) -> bool:
        current_time = time.time()
        _ = not player_name in self.interact_time_dict or (current_time - self.interact_time_dict[player_name]) > 0.125
        if _:
            self.interact_time_dict[player_name] = current_time
            return True
        else:
            return False

    # Displayer
    def display_single_color(self, color: str):
        # lime white red
        if self.current_facility is not None:
            self.server.dispatch_command(self.server.command_sender,
                                         self.get_fill_command(self.current_facility['screen_start'], self.current_facility['screen_end'], f'{color}_wool'))
            # f'fill {' '.join([str(_) for _ in self.current_facility['screen_start']])} {' '.join([str(_) for _ in self.current_facility['screen_end']])} {color}_wool'

    def displayer_game_update(self, new_seq: list):
        for _ in range(5):
            self.displayer_line_update(_, self.current_display_seq[_], new_seq[_])
        self.current_display_seq = new_seq

    def displayer_line_update(self, row: int, current_black_tile_pos: int, new_black_tile_pos: int):
        if new_black_tile_pos is None:
            for c in range(4):
                self.displayer_tile_update(row, c, 'green')
            return
        else:
            if current_black_tile_pos is None:
                for c in range(4):
                    if c == new_black_tile_pos:
                        self.displayer_tile_update(row, c, 'black')
                    else:
                        self.displayer_tile_update(row, c, 'white')
            else:
                if current_black_tile_pos == new_black_tile_pos:
                    return
                self.displayer_tile_update(row, current_black_tile_pos, 'white')
                self.displayer_tile_update(row, new_black_tile_pos, 'black')

    def displayer_tile_update(self, row: int, column: int, color: str):
        if self.current_facility['screen_start'][0] == self.current_facility['screen_end'][0]:
            if self.current_facility['screen_start'][2] > self.current_facility['screen_end'][2]:
                adjust = -1
            else:
                adjust = 1
            block_pos = (self.current_facility['screen_start'][0],
                         self.current_facility['screen_start'][1] + row,
                         self.current_facility['screen_start'][2] + column * adjust)
        elif self.current_facility['screen_start'][2] == self.current_facility['screen_end'][2]:
            if self.current_facility['screen_start'][0] > self.current_facility['screen_end'][0]:
                adjust = -1
            else:
                adjust = 1
            block_pos = (self.current_facility['screen_start'][0] + column * adjust,
                         self.current_facility['screen_start'][1] + row,
                         self.current_facility['screen_start'][2])
        else:
            self.logger.error('[ARC DTWT]An error occurred while updating screen, please recreate game facility.')
            return
        # self.server.dispatch_command(self.server.command_sender, f'fill {' '.join([str(_) for _ in block_pos])} {' '.join([str(_) for _ in block_pos])} {color}_wool')
        self.server.dispatch_command(self.server.command_sender, self.get_fill_command(block_pos, block_pos, f'{color}_wool'))

    def convert_world_pos_to_screen_pos(self, world_pos: tuple[float, float, float]):
        if self.current_facility['screen_start'][0] == self.current_facility['screen_end'][0]:
            if self.judge_if_number_in_range(self.current_facility['screen_start'][2], self.current_facility['screen_end'][2], world_pos[2]) \
                and self.current_facility['screen_start'][1] <= world_pos[1] <= self.current_facility['screen_end'][1]:
                return math.fabs(world_pos[2] - self.current_facility['screen_start'][2]), world_pos[1] - self.current_facility['screen_start'][1]
        elif self.current_facility['screen_start'][2] == self.current_facility['screen_end'][2]:
            if self.judge_if_number_in_range(self.current_facility['screen_start'][0], self.current_facility['screen_end'][0], world_pos[0]) \
                and self.current_facility['screen_start'][1] <= world_pos[1] <= self.current_facility['screen_end'][1]:
                return math.fabs(world_pos[0] - self.current_facility['screen_start'][0]), world_pos[1] - self.current_facility['screen_start'][1]
        else:
            self.logger.error('[ARC DTWT]An error occurred while calculating player clicked position, please recreate game facility.')
            return None

    # Player record
    def update_player_record(self, xuid: str, player_name: str, time: float) -> tuple[bool, bool]:
        """
        更新玩家记录
        :param xuid: 玩家的XUID
        :param player_name: 玩家名称
        :param time: 完成用时
        :return: (是否更新成功, 是否破纪录)
        """
        today = date.today().isoformat()
        
        # 查询现有记录
        existing_record = self.db_manager.query_one(
            "SELECT * FROM player_records WHERE xuid = ?",
            (xuid,)
        )

        if existing_record is None:
            # 玩家不存在，插入新记录
            success = self.db_manager.insert("player_records", {
                "xuid": xuid,
                "player_name": player_name,
                "best_record": time,
                "last_play_date": today
            })
            return success, True  # 新玩家，算作破纪录
        else:
            # 更新最后游戏日期
            update_data = {"player_name": player_name, "last_play_date": today}
            is_new_record = False
            
            if time < existing_record["best_record"]:
                # 新记录更好，更新记录
                update_data["best_record"] = time
                is_new_record = True
            
            success = self.db_manager.update(
                "player_records",
                update_data,
                "xuid = ?",
                (xuid,)
            )
            return success, is_new_record

    def get_player_best_time(self, xuid: str) -> Optional[float]:
        """
        获取指定玩家的最佳用时
        :param xuid: 玩家XUID
        :return: 玩家最佳用时，如果玩家不存在返回None
        """
        result = self.db_manager.query_one(
            "SELECT best_record FROM player_records WHERE xuid = ?",
            (xuid,)
        )
        return result["best_record"] if result else None

    def get_player_rank(self, xuid: str) -> Optional[int]:
        """
        获取玩家排名
        :param xuid: 玩家XUID
        :return: 玩家排名（从1开始），未找到返回None
        """
        sql = """
        WITH RankedPlayers AS (
            SELECT xuid, 
                   ROW_NUMBER() OVER (ORDER BY best_record ASC) as rank
            FROM player_records
        )
        SELECT rank
        FROM RankedPlayers
        WHERE xuid = ?
        """
        result = self.db_manager.query_one(sql, (xuid,))
        return result["rank"] if result else None

    def get_leaderboard(self, limit: int, reverse: bool = False) -> List[Tuple[str, float]]:
        """
        获取排行榜
        :param limit: 获取数量
        :param reverse: 是否倒序（获取最慢记录）
        :return: [(玩家名, 用时)] 的列表
        """
        order = "DESC" if reverse else "ASC"
        sql = f"""
        SELECT player_name, best_record
        FROM player_records
        ORDER BY best_record {order}
        LIMIT ?
        """
        results = self.db_manager.query_all(sql, (limit,))
        return [(record["player_name"], record["best_record"]) for record in results]

    def get_average_time(self) -> Optional[float]:
        """
        获取所有玩家的平均用时
        :return: 平均用时，无记录返回None
        """
        sql = "SELECT AVG(best_record) as avg_time FROM player_records"
        result = self.db_manager.query_one(sql)
        return result["avg_time"] if result else None

    def can_receive_daily_reward(self, xuid: str) -> bool:
        """
        检查玩家是否可以获得每日奖励
        :param xuid: 玩家XUID
        :return: 是否可以获得每日奖励
        """
        today = date.today().isoformat()
        
        result = self.db_manager.query_one(
            "SELECT last_play_date FROM player_records WHERE xuid = ?",
            (xuid,)
        )
        
        if result is None:
            return True  # 新玩家，可以获得奖励
        
        last_play_date = result.get("last_play_date")
        return last_play_date != today  # 如果不是今天玩的，可以获得奖励

    def give_money_to_player(self, player: Player, amount: int, reason: str) -> bool:
        """
        给玩家金钱奖励
        :param player: 玩家对象
        :param amount: 金钱数量
        :param reason: 奖励原因
        :return: 是否成功
        """
        if self.economy_plugin is None:
            player.send_message(self.language_manager.GetText('DTWT_ECONOMY_NOT_AVAILABLE'))
            return False
        
        try:
            # 使用umoney插件API给玩家金钱
            self.economy_plugin.api_change_player_money(player.name, amount)
            
            # 根据奖励类型发送不同的消息
            if "每日" in reason:
                player.send_message(self.language_manager.GetText('DTWT_DAILY_REWARD_MESSAGE').format(amount))
            elif reason.isdigit():
                # reason 是排名数字，比如 "1", "2", "3"
                player.send_message(self.language_manager.GetText('DTWT_RANK_REWARD_MESSAGE').format(reason, amount))
            return True
        except Exception as e:
            self.logger.warning(f"[ARC DTWT]Failed to give money to player {player.name}: {e}")
            player.send_message(self.language_manager.GetText('DTWT_ECONOMY_NOT_AVAILABLE'))
            return False

    def check_and_give_rank_reward(self, player: Player, new_rank: int) -> None:
        """
        检查并发放排名奖励
        :param player: 玩家对象
        :param new_rank: 新排名
        """
        if new_rank == 1:
            self.give_money_to_player(player, self.first_place_reward, str(new_rank))
        elif new_rank == 2:
            self.give_money_to_player(player, self.second_place_reward, str(new_rank))
        elif new_rank == 3:
            self.give_money_to_player(player, self.third_place_reward, str(new_rank))

    # Static function tools
    @staticmethod
    def judge_if_number_in_range(range_a, range_b, number) -> bool:
        return range_a <= number <= range_b if range_a <= range_b else range_b <= number <= range_a

    @staticmethod
    def get_fill_command(pos1: tuple, pos2: tuple, block_name: str) -> str:
        return f'fill {' '.join([str(_) for _ in pos1])} {' '.join([str(_) for _ in pos2])} {block_name}'

    # Database
    def _init_database(self):
        """初始化数据库表结构"""
        # 游戏设施信息表
        self.db_manager.create_table("game_facilities", {
            "id": "INTEGER PRIMARY KEY AUTOINCREMENT",
            "screen_start_x": "INTEGER NOT NULL",
            "screen_start_y": "INTEGER NOT NULL",
            "screen_start_z": "INTEGER NOT NULL",
            "screen_end_x": "INTEGER NOT NULL",
            "screen_end_y": "INTEGER NOT NULL",
            "screen_end_z": "INTEGER NOT NULL",
            "trigger_x": "INTEGER NOT NULL",
            "trigger_y": "INTEGER NOT NULL",
            "trigger_z": "INTEGER NOT NULL"
        })

        # 玩家记录表
        self.db_manager.create_table("player_records", {
            "xuid": "TEXT PRIMARY KEY",
            "player_name": "TEXT NOT NULL",
            "best_record": "REAL NOT NULL",
            "last_play_date": "TEXT"
        })
        
        # 检查并添加缺失的列（用于数据库迁移）
        self._migrate_database()

    def _migrate_database(self):
        """数据库迁移：检查并添加缺失的列"""
        try:
            # 检查player_records表是否存在last_play_date列
            columns_info = self.db_manager.query_all("PRAGMA table_info(player_records)")
            column_names = [col['name'] for col in columns_info] if columns_info else []
            
            if 'last_play_date' not in column_names:
                # 添加缺失的last_play_date列
                self.db_manager.execute("ALTER TABLE player_records ADD COLUMN last_play_date TEXT")
                print("[ARC DTWT]已为player_records表添加last_play_date列")
        except Exception as e:
            print(f"[ARC DTWT]数据库迁移时出现错误: {e}")

    def update_game_facility(self, screen_start: tuple, screen_end: tuple, trigger_pos: tuple) -> bool:
        """
        更新游戏设施信息
        :param screen_start: 显示屏起点坐标 (x, y, z)
        :param screen_end: 显示屏终点坐标 (x, y, z)
        :param trigger_pos: 触发方块坐标 (x, y, z)
        :return: 是否更新成功
        """
        # 首先删除所有现有记录
        self.db_manager.execute("DELETE FROM game_facilities")

        # 插入新记录
        return self.db_manager.insert("game_facilities", {
            "screen_start_x": screen_start[0],
            "screen_start_y": screen_start[1],
            "screen_start_z": screen_start[2],
            "screen_end_x": screen_end[0],
            "screen_end_y": screen_end[1],
            "screen_end_z": screen_end[2],
            "trigger_x": trigger_pos[0],
            "trigger_y": trigger_pos[1],
            "trigger_z": trigger_pos[2]
        })

    def get_game_facility(self) -> Optional[Dict[str, Any]]:
        """
        获取游戏设施信息
        :return: 返回游戏设施信息字典，如果不存在则返回None
        格式：{
            'dimension': str,
            'screen_start': tuple(x, y, z),
            'screen_end': tuple(x, y, z),
            'trigger_pos': tuple(x, y, z)
        }
        """
        result = self.db_manager.query_one("SELECT * FROM game_facilities LIMIT 1")

        if result is None:
            return None

        return {
            'screen_start': (
                result['screen_start_x'],
                result['screen_start_y'],
                result['screen_start_z']
            ),
            'screen_end': (
                result['screen_end_x'],
                result['screen_end_y'],
                result['screen_end_z']
            ),
            'trigger_pos': (
                result['trigger_x'],
                result['trigger_y'],
                result['trigger_z']
            )
        }

    def _get_qq_sync_plugin(self):
        """Resolve ARC QQ Sync plugin (AstrBot hub id first, legacy id fallback).

        Endstone 会把 entry-point 里的 '-' 转成 '_'，故优先查找 arc_qq_sync_astrbot。
        """
        pm = self.server.plugin_manager
        for name in (
            "arc_qq_sync_astrbot",
            "arc-qq-sync-astrbot",
            "qqsync_plugin",
        ):
            plug = pm.get_plugin(name)
            if plug is not None:
                return plug
        return None

    def send_to_qq_group(self, message: str):
        """
        发送消息到QQ群（经弧光 EndStone 消息中枢）。
        优先 api_send_raw（自动加服务器前缀），其次 api_send_message。
        """
        try:
            qqsync = self._get_qq_sync_plugin()
            if qqsync is None:
                self.logger.warning("[弧光·别踩白块] QQ Sync 插件未找到，无法发送群消息")
                return

            if hasattr(qqsync, "api_send_raw"):
                success = qqsync.api_send_raw(message)
            elif hasattr(qqsync, "api_send_message"):
                success = qqsync.api_send_message(message)
            else:
                self.logger.warning("[弧光·别踩白块] QQ Sync 无可用发送 API")
                return

            if success:
                self.logger.info(f"[弧光·别踩白块] 群消息已发送: {message[:80]}...")
            else:
                self.logger.warning(f"[弧光·别踩白块] 群消息发送失败: {message[:80]}...")
        except Exception as e:
            self.logger.error(f"[弧光·别踩白块] QQ群消息发送异常: {str(e)}")
            # 即使QQ群发送失败，也不影响游戏正常运行