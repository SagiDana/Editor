#!/home/sagid/.pyenv/versions/3.11.8/bin/python3.11

from string import printable
import traceback
import argparse
import json
import re
import os

from .buffer import Buffer
from .common import Scope
from .settings import *
from .task import Task
from .screen import *
from .log import elog
from .tab import Tab

from .events import *
from .hooks import *
from .popup import *

from .plugins import yank_to_clipboard, paste_from_clipboard
from .plugins import comment
from .plugins import ripgrep
from .plugins import format
from .plugins import doc, doc_get_latest_file
from .plugins import fzf, rg_fzf
from .plugins import gotovim
from .plugins import gd

from .utils import *

args = None
pending_buffer = b''

NORMAL = 'normal'
INSERT = 'insert'
VISUAL = 'visual'
VISUAL_LINE = 'visual_line'
VISUAL_BLOCK = 'visual_block'
REPLACE = 'replace'
MULTI_CURSOR_NORMAL = 'multi_cursor_normal'
MULTI_CURSOR_INSERT = 'multi_cursor_insert'

class Editor():
    def on_buffer_destroy_after_callback(self, buf):
        self.buffers.remove(buf)

    def on_buffer_create_after_callback(self, buf):
        self.buffers.append(buf)

    def on_key_callback(self, key):
        self.internal_registers["."].append(key)

    def draw(self):
        self.get_curr_tab().draw()

    def change_begin(self):
        self.get_curr_window().change_begin()

    def change_end(self):
        self.get_curr_window().change_end()

        self.registers["."] = self.internal_registers["."].copy()
        self.internal_registers["."] = []

    def change_mode(self, target, effect_change=True):
        # escape while in normal mode is a no-op (or is it?;)
        if self.mode == NORMAL and target == NORMAL:
            # just clear the search highlights, this is driving me crazy
            self.get_curr_buffer().clear_highlights()
            self.get_curr_window().draw()
        if self.mode == INSERT and target == NORMAL:
            y = self.get_curr_window().buffer_cursor[1]
            line = self.get_curr_window().get_line(y)
            if re.match(r'^\s*$', line):
                self.get_curr_window().empty_line(y)
            if effect_change: self.change_end()
            self.get_curr_window().move_left()
            self.screen.set_cursor_block_blink()
        if self.mode == NORMAL and target == INSERT:
            if effect_change: self.change_begin()
            self.screen.set_cursor_i_beam()
        if self.mode == NORMAL and target == VISUAL_LINE:
            self.get_curr_window().visual_begin(VISUAL_LINE)
        if self.mode == NORMAL and target == VISUAL_BLOCK:
            self.get_curr_window().visual_begin(VISUAL_BLOCK)
        if self.mode == NORMAL and target == VISUAL:
            self.get_curr_window().visual_begin(VISUAL)
        if self.mode == VISUAL and target == NORMAL:
            self.get_curr_window().visual_end()
        if self.mode == VISUAL and target == INSERT:
            self.get_curr_window().visual_end()
            self.screen.set_cursor_i_beam()
        if self.mode == VISUAL_LINE and target == NORMAL:
            self.get_curr_window().visual_end()
        if self.mode == VISUAL_LINE and target == INSERT:
            self.get_curr_window().visual_end()
            self.screen.set_cursor_i_beam()
        if self.mode == VISUAL_BLOCK and target == NORMAL:
            self.get_curr_window().visual_end()
        if self.mode == NORMAL and target == REPLACE:
            self.screen.set_cursor_underline()
            self.change_begin()
            self._replace_line = self.get_curr_window().get_curr_line()
            self._replace_x = self.get_curr_window().buffer_cursor[0]
            self._replace_y = self.get_curr_window().buffer_cursor[1]
        if self.mode == REPLACE and target == NORMAL:
            self.change_end()
            self.screen.set_cursor_block_blink()
            self._replace_line = ""
            self._replace_x = -1
            self._replace_y = -1
        if self.mode == NORMAL and target == MULTI_CURSOR_NORMAL:
            pass
        if self.mode == MULTI_CURSOR_INSERT and target == MULTI_CURSOR_NORMAL:
            # y = self.get_curr_window().buffer_cursor[1]
            # line = self.get_curr_window().get_line(y)
            # if re.match(r'^\s*$', line):
                # self.get_curr_window().empty_line(y)
            if effect_change: self.change_end()
        if self.mode == MULTI_CURSOR_NORMAL and target == MULTI_CURSOR_INSERT:
            if effect_change: self.change_begin()

        self.mode = target
        self.curr_maps = self.maps[self.mode]

    def _initialize_normal_window_maps(self):
        self.maps[NORMAL][CTRL_W_KEY] = {}
        def ctrl_w_s_map(self):
            self.get_curr_tab().split()
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('s')] = ctrl_w_s_map
        self.maps[NORMAL][CTRL_W_KEY][CTRL_S_KEY] = ctrl_w_s_map
        def ctrl_w_v_map(self):
            self.get_curr_tab().vsplit()
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('v')] = ctrl_w_v_map
        self.maps[NORMAL][CTRL_W_KEY][CTRL_V_KEY] = ctrl_w_v_map
        def ctrl_w_h_map(self):
            self.get_curr_tab().move_to_left_window()
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('h')] = ctrl_w_h_map
        self.maps[NORMAL][CTRL_W_KEY][CTRL_H_KEY] = ctrl_w_h_map
        def ctrl_w_j_map(self):
            self.get_curr_tab().move_to_down_window()
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('j')] = ctrl_w_j_map
        self.maps[NORMAL][CTRL_W_KEY][CTRL_J_KEY] = ctrl_w_j_map
        def ctrl_w_k_map(self):
            self.get_curr_tab().move_to_up_window()
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('k')] = ctrl_w_k_map
        self.maps[NORMAL][CTRL_W_KEY][CTRL_K_KEY] = ctrl_w_k_map
        def ctrl_w_l_map(self):
            self.get_curr_tab().move_to_right_window()
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('l')] = ctrl_w_l_map
        self.maps[NORMAL][CTRL_W_KEY][CTRL_L_KEY] = ctrl_w_l_map
        def ctrl_w_w_map(self):
            self.get_curr_tab().zoom_toggle()
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('w')] = ctrl_w_w_map
        self.maps[NORMAL][CTRL_W_KEY][CTRL_W_KEY] = ctrl_w_w_map
        def ctrl_w_t_map(self):
            self._create_tab(self.get_curr_buffer())
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('t')] = ctrl_w_t_map
        self.maps[NORMAL][CTRL_W_KEY][CTRL_T_KEY] = ctrl_w_t_map
        def ctrl_w_H_map(self):
            elog("ctrl_w_H_map")
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('H')] = ctrl_w_H_map
        def ctrl_w_J_map(self):
            elog("ctrl_w_J_map")
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('J')] = ctrl_w_J_map
        def ctrl_w_K_map(self):
            elog("ctrl_w_K_map")
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('K')] = ctrl_w_K_map
        def ctrl_w_L_map(self):
            elog("ctrl_w_L_map")
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('L')] = ctrl_w_L_map
        def ctrl_w_colon_map(self):
            elog("ctrl_w_colon_map")
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord(',')] = ctrl_w_colon_map
        def ctrl_w_m_map(self):
            elog("ctrl_w_m_map")
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('m')] = ctrl_w_m_map
        def ctrl_w_dot_map(self):
            elog("ctrl_w_dot_map")
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('.')] = ctrl_w_dot_map
        def ctrl_w_n_map(self):
            elog("ctrl_w_n_map")
            return False
        self.maps[NORMAL][CTRL_W_KEY][ord('n')] = ctrl_w_n_map

    def __initialize_movement_objects_maps(self, maps, callbacks):
        default_callback = callbacks.get('default', None)
        def move_(self): pass
        def move_j(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            if src_y >= len(self.get_curr_buffer().lines) - 1:
                dst_y = src_y
                dst_x = src_x
            else:
                dst_y = src_y + 1
                dst_x = min(src_x, len(self.get_curr_buffer().lines[dst_y]) - 1)
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('j'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('j')] = move_j
        def move_k(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            if src_y == 0:
                dst_y = src_y
                dst_x = src_x
            else:
                dst_y = src_y - 1
                dst_x = min(src_x, len(self.get_curr_buffer().lines[dst_y]) - 1)
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('k'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('k')] = move_k
        def move_h(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            dst_y = src_y
            dst_x = max(src_x - 1, 0)

            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('h'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('h')] = move_h
        def move_l(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            dst_y = src_y
            dst_x = min(src_x + 1, len(self.get_curr_buffer().lines[src_y]) - 1)

            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('h'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('l')] = move_l
        def move_w(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]
            ret = self.get_curr_buffer().find_next_word(src_x, src_y)
            if not ret: return False
            dst_x, dst_y = ret
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('w'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('w')] = move_w
        def move_W(self):
            start_x = self.get_curr_window().buffer_cursor[0]
            start_y = self.get_curr_window().buffer_cursor[1]
            ret = self.get_curr_buffer().find_next_WORD(start_x, start_y)
            if not ret: return False
            end_x, end_y = ret
            scope = Scope(start_x, start_y, end_x, end_y)
            if scope:
                cb = callbacks.get(ord('W'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('W')] = move_W
        def move_dash(self):
            start_x = self.get_curr_window().buffer_cursor[0]
            start_y = self.get_curr_window().buffer_cursor[1]
            ret = self.get_curr_buffer().find_next_w_o_r_d(start_x, start_y)
            if not ret: return False
            end_x, end_y = ret
            scope = Scope(start_x, start_y, end_x, end_y)
            if scope:
                cb = callbacks.get(ord('-'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('-')] = move_dash
        def move_e(self):
            start_x = self.get_curr_window().buffer_cursor[0]
            start_y = self.get_curr_window().buffer_cursor[1]
            ret = self.get_curr_buffer().find_word_end(start_x, start_y)
            if not ret: return False
            end_x, end_y = ret
            scope = Scope(start_x, start_y, end_x, end_y)
            if scope:
                cb = callbacks.get(ord('e'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('e')] = move_e
        def move_E(self):
            start_x = self.get_curr_window().buffer_cursor[0]
            start_y = self.get_curr_window().buffer_cursor[1]
            ret = self.get_curr_buffer().find_WORD_end(start_x, start_y)
            if not ret: return False
            end_x, end_y = ret
            scope = Scope(start_x, start_y, end_x, end_y)
            if scope:
                cb = callbacks.get(ord('E'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('E')] = move_E
        def move_underscore(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]
            ret = self.get_curr_buffer().find_prev_w_o_r_d(src_x, src_y)
            if not ret: return False
            dst_x, dst_y = ret
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('_'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('_')] = move_underscore
        def move_b(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]
            ret = self.get_curr_buffer().find_prev_word(src_x, src_y)
            if not ret: return False
            dst_x, dst_y = ret
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('b'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('b')] = move_b
        def move_B(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]
            ret = self.get_curr_buffer().find_prev_WORD(src_x, src_y)
            if not ret: return False
            dst_x, dst_y = ret
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('B'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('B')] = move_B
        def move_dollar(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            dst_y = src_y
            dst_x = len(self.get_curr_buffer().lines[dst_y]) - 1
            dst_x -= 1 # exclude newline
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('$'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('$')] = move_dollar
        def move_caret(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            dst_y = src_y
            m = re.match(r'^\s*', self.get_curr_buffer().lines[dst_y])
            dst_x = 0 if not m else len(m[0])

            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('^'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('^')] = move_caret
        def move_zero(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            dst_y = src_y
            dst_x = 0

            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('0'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('0')] = move_zero
        def move_f_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            try:
                char = chr(self.screen.get_key())
                loc = self.get_curr_buffer().find_next_char(src_x,
                                                            src_y,
                                                            char)
                if not loc: return False
                self._action = 'f'
                self._char = char
                dst_x, dst_y = loc[0], loc[1]
                scope = Scope(src_x, src_y, dst_x, dst_y)
                if scope:
                    cb = callbacks.get(ord('f'), default_callback)
                    if cb is not None: return cb(scope)
            except Exception as e: elog(f"{e}")
        maps[ord('f')] = move_f_map
        def move_F_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            try:
                char = chr(self.screen.get_key())
                loc = self.get_curr_buffer().find_prev_char(src_x,
                                                            src_y,
                                                            char)
                if not loc: return False
                self._action = 'F'
                self._char = char
                dst_x, dst_y = loc[0], loc[1]
                scope = Scope(src_x, src_y, dst_x, dst_y)
                if scope:
                    cb = callbacks.get(ord('F'), default_callback)
                    if cb is not None: return cb(scope)
            except Exception as e: elog(f"{e}")
        maps[ord('F')] = move_F_map
        def move_t_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            try:
                char = chr(self.screen.get_key())
                loc = self.get_curr_buffer().find_next_char(src_x,
                                                            src_y,
                                                            char)
                if not loc: return False
                self._action = 't'
                self._char = char
                dst_x, dst_y = loc[0], loc[1]
                dst_x = dst_x - 1 if dst_x > 0 else dst_x

                scope = Scope(src_x, src_y, dst_x, dst_y)
                if scope:
                    cb = callbacks.get(ord('t'), default_callback)
                    if cb is not None: return cb(scope)
            except Exception as e: elog(f"{e}")
        maps[ord('t')] = move_t_map
        def move_T_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            try:
                char = chr(self.screen.get_key())
                loc = self.get_curr_buffer().find_prev_char(src_x,
                                                            src_y,
                                                            char)
                if not loc: return False
                self._action = 'T'
                self._char = char
                dst_x, dst_y = loc[0], loc[1]
                dst_x = dst_x + 1 if dst_x < len(self.get_curr_window().get_line(dst_y)) - 1 else dst_x

                scope = Scope(src_x, src_y, dst_x, dst_y)
                if scope:
                    cb = callbacks.get(ord('T'), default_callback)
                    if cb is not None: return cb(scope)
            except Exception as e: elog(f"{e}")
        maps[ord('T')] = move_T_map
        def semicolon_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]
            dst_x, dst_y = None, None

            if self._action == 'f':
                loc = self.get_curr_buffer().find_next_char(src_x, src_y, self._char)
                if not loc: return
                dst_x, dst_y = loc[0], loc[1]
            if self._action == 'F':
                loc = self.get_curr_buffer().find_prev_char(src_x, src_y, self._char)
                if not loc: return
                dst_x, dst_y = loc[0], loc[1]
            if self._action == 't':
                loc = self.get_curr_buffer().find_next_char(src_x, src_y, self._char)
                if not loc: return
                dst_x, dst_y = loc[0], loc[1]
                dst_x = dst_x - 1 if dst_x > 0 else dst_x
                # in the case we found ourselves, increase yourself
                if dst_x == src_x and dst_y == src_y:
                    loc = self.get_curr_buffer().find_next_char(src_x + 1, src_y, self._char)
                    if not loc: return
                    dst_x, dst_y = loc[0], loc[1]
                    dst_x = dst_x - 1 if dst_x > 0 else dst_x
            if self._action == 'T':
                loc = self.get_curr_buffer().find_prev_char(src_x, src_y, self._char)
                if not loc: return
                dst_x, dst_y = loc[0], loc[1]
                dst_x = dst_x + 1 if dst_x < len(self.get_curr_window().get_line(dst_y)) - 1 else dst_x
                # in the case we found ourselves, decrease yourself
                if dst_x == src_x and dst_y == src_y:
                    loc = self.get_curr_buffer().find_prev_char(src_x - 1, src_y, self._char)
                    if not loc: return
                    dst_x, dst_y = loc[0], loc[1]
                    dst_x = dst_x + 1 if dst_x < len(self.get_curr_window().get_line(dst_y)) - 1 else dst_x
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord(';'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord(';')] = semicolon_map
        def comma_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]
            dst_x, dst_y = None, None

            if self._action == 'f':
                loc = self.get_curr_buffer().find_prev_char(src_x, src_y, self._char)
                if not loc: return
                dst_x, dst_y = loc[0], loc[1]
            if self._action == 'F':
                loc = self.get_curr_buffer().find_next_char(src_x, src_y, self._char)
                if not loc: return
                dst_x, dst_y = loc[0], loc[1]
            if self._action == 't':
                loc = self.get_curr_buffer().find_prev_char(src_x, src_y, self._char)
                if not loc: return
                dst_x, dst_y = loc[0], loc[1]
                dst_x = dst_x + 1 if dst_x < len(self.get_curr_window().get_line(dst_y)) - 1 else dst_x
                # in the case we found ourselves, decrease yourself
                if dst_x == src_x and dst_y == src_y:
                    loc = self.get_curr_buffer().find_prev_char(src_x - 1, src_y, self._char)
                    if not loc: return
                    dst_x, dst_y = loc[0], loc[1]
                    dst_x = dst_x + 1 if dst_x < len(self.get_curr_window().get_line(dst_y)) - 1 else dst_x
            if self._action == 'T':
                loc = self.get_curr_buffer().find_next_char(src_x, src_y, self._char)
                if not loc: return
                dst_x, dst_y = loc[0], loc[1]
                dst_x = dst_x - 1 if dst_x > 0 else dst_x
                # in the case we found ourselves, increase yourself
                if dst_x == src_x and dst_y == src_y:
                    loc = self.get_curr_buffer().find_next_char(src_x + 1, src_y, self._char)
                    if not loc: return
                    dst_x, dst_y = loc[0], loc[1]
                    dst_x = dst_x - 1 if dst_x > 0 else dst_x
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord(','), default_callback)
                if cb is not None: return cb(scope)
        maps[ord(',')] = comma_map
        def precent_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            char = self.get_curr_window().get_curr_line()[src_x]
            dst_char = self.get_curr_buffer().negate_char(char)
            if not dst_char: return False
            if char in "(<{[":
                ret = self.get_curr_buffer().find_next_char(src_x, src_y, dst_char, smart=True)
                if not ret: return False
                dst_x, dst_y = ret
            else:
                ret = self.get_curr_buffer().find_prev_char(src_x, src_y, dst_char, smart=True)
                if not ret: return False
                dst_x, dst_y = ret
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('%'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('%')] = precent_map
        def H_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            dst_x, dst_y = self.get_curr_window().get_begin_visible()
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('H'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('H')] = H_map
        def M_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            dst_x, dst_y = self.get_curr_window().get_middle_visible()
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('M'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('M')] = M_map
        def L_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            dst_x, dst_y = self.get_curr_window().get_end_visible()
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('L'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('L')] = L_map
        def ctrl_u_map(self):
            start_x = self.get_curr_window().buffer_cursor[0]
            start_y = self.get_curr_window().buffer_cursor[1]
            end_x, end_y = self.get_curr_window().get_half_page_up()
            scope = Scope(start_x, start_y, end_x, end_y)
            if scope:
                cb = callbacks.get(CTRL_U_KEY, default_callback)
                if cb is not None: return cb(scope)
        maps[CTRL_U_KEY] = ctrl_u_map
        def ctrl_d_map(self):
            start_x = self.get_curr_window().buffer_cursor[0]
            start_y = self.get_curr_window().buffer_cursor[1]
            end_x, end_y = self.get_curr_window().get_half_page_down()
            scope = Scope(start_x, start_y, end_x, end_y)
            if scope:
                cb = callbacks.get(CTRL_D_KEY, default_callback)
                if cb is not None: return cb(scope)
        maps[CTRL_D_KEY] = ctrl_d_map
        def n_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            pattern = self.registers['/']
            results = self.get_curr_buffer().search_pattern(pattern)
            if len(results) == 0: return False
            pos = self._find_closest_match(src_x, src_y, results, self._search_forward)
            if not pos: return False
            dst_x, dst_y = pos[0], pos[1]
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('n'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('n')] = n_map
        def N_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            pattern = self.registers['/']
            results = self.get_curr_buffer().search_pattern(pattern)
            if len(results) == 0: return False
            pos = self._find_closest_match(src_x, src_y, results, not self._search_forward)
            if not pos: return False
            dst_x, dst_y = pos[0], pos[1]
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('N'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('N')] = N_map

        default_close_bracket_callbacks = callbacks.get(ord(']'), {})
        default_open_bracket_callbacks = callbacks.get(ord('['), {})

        if ord(']') not in maps: maps[ord(']')] = {}
        if ord('[') not in maps: maps[ord('[')] = {}
        def bracket_close_m_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]
            ret = self.get_curr_buffer().find_next_method(src_x, src_y)
            if not ret: return False
            dst_x, dst_y = ret
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = default_close_bracket_callbacks.get(ord('m'), default_callback)
                if cb is not None: return cb(scope)
        if type(maps[ord(']')]) is dict and ord('m') not in maps[ord(']')]:
            maps[ord(']')][ord('m')] = bracket_close_m_map
        def bracket_open_m_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]
            ret = self.get_curr_buffer().find_prev_method(src_x, src_y)
            if not ret: return False
            dst_x, dst_y = ret
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = default_open_bracket_callbacks.get(ord('m'), default_callback)
                if cb is not None: return cb(scope)
        if type(maps[ord('[')]) is dict and ord('m') not in maps[ord('[')]:
            maps[ord('[')][ord('m')] = bracket_open_m_map
        def bracket_close_M_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]
            ret = self.get_curr_buffer().find_method_end(src_x, src_y)
            if not ret: return False
            dst_x, dst_y = ret
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = default_close_bracket_callbacks.get(ord('M'), default_callback)
                if cb is not None: return cb(scope)
        if type(maps[ord(']')]) is dict and ord('M') not in maps[ord(']')]:
            maps[ord(']')][ord('M')] = bracket_close_M_map
        def bracket_open_M_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]
            ret = self.get_curr_buffer().find_method_begin(src_x, src_y)
            if not ret: return False
            dst_x, dst_y = ret
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = default_open_bracket_callbacks.get(ord('M'), default_callback)
                if cb is not None: return cb(scope)
        if type(maps[ord('[')]) is dict and ord('M') not in maps[ord('[')]:
            maps[ord('[')][ord('M')] = bracket_open_M_map
        def G_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            dst_y = len(self.get_curr_buffer().lines) - 1
            dst_x = len(self.get_curr_buffer().lines[dst_y]) - 1
            dst_x -= 1 # exclude newline
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = callbacks.get(ord('G'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('G')] = G_map
        default_g_callbacks = callbacks.get(ord('g'), {})
        if ord('g') not in maps: maps[ord('g')] = {}
        def gg_map(self):
            src_x = self.get_curr_window().buffer_cursor[0]
            src_y = self.get_curr_window().buffer_cursor[1]

            dst_x, dst_y = 0, 0
            scope = Scope(src_x, src_y, dst_x, dst_y)
            if scope:
                cb = default_g_callbacks.get(ord('g'), default_callback)
                if cb is not None: return cb(scope)
        if not maps[ord('g')]: maps[ord('g')] = {}
        maps[ord('g')][ord('g')] = gg_map

    def __initialize_inner_around_objects_maps(self, maps, callbacks):
        default_callback = callbacks.get('default', None)
        default_i_callbacks = callbacks.get(ord('i'), {})
        default_a_callbacks = callbacks.get(ord('a'), {})
        maps[ord('i')] = {}
        def inner_parentheses(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_parentheses(x, y)
            if scope:
                cb = default_i_callbacks.get(ord('('), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord('(')] = inner_parentheses
        maps[ord('i')][ord(')')] = inner_parentheses
        maps[ord(')')] = inner_parentheses
        maps[ord('(')] = inner_parentheses
        def inner_square_brackets(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_square_brackets(x, y)
            if scope:
                cb = default_i_callbacks.get(ord('['), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord('[')] = inner_square_brackets
        maps[ord('i')][ord(']')] = inner_square_brackets
        maps[ord('[')] = inner_square_brackets
        maps[ord(']')] = inner_square_brackets
        def inner_curly_brackets(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_curly_brackets(x, y)
            if scope:
                cb = default_i_callbacks.get(ord('{'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord('{')] = inner_curly_brackets
        maps[ord('i')][ord('}')] = inner_curly_brackets
        maps[ord('}')] = inner_curly_brackets
        maps[ord('{')] = inner_curly_brackets
        def inner_greater_than(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_greater_than(x, y)
            if scope:
                cb = default_i_callbacks.get(ord('<'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord('<')] = inner_greater_than
        maps[ord('i')][ord('>')] = inner_greater_than
        maps[ord('<')] = inner_greater_than
        maps[ord('>')] = inner_greater_than
        def inner_quotation(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_quotation(x, y)
            if scope:
                cb = default_i_callbacks.get(ord('"'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord('"')] = inner_quotation
        maps[ord('"')] = inner_quotation
        def inner_apostrophe(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_apostrophe(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("'"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("'")] = inner_apostrophe
        maps[ord("'")] = inner_apostrophe
        def inner_backtick(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_backtick(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("`"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("`")] = inner_backtick
        maps[ord("`")] = inner_backtick
        def inner_word(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_word(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("w"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("w")] = inner_word
        def inner_w_o_r_d(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_w_o_r_d(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("_"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("_")] = inner_w_o_r_d
        def inner_WORD(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_WORD(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("W"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("W")] = inner_WORD

        # code objects here...
        def inner_if(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_if(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("f"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("f")] = inner_if
        def inner_IF(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_IF(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("F"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("F")] = inner_IF
        def inner_for(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_for(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("r"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("r")] = inner_for
        def inner_FOR(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_FOR(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("R"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("R")] = inner_FOR
        def inner_else(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_else(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("l"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("l")] = inner_else
        def inner_while(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_while(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("e"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("e")] = inner_while
        def inner_WHILE(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_WHILE(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("E"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("E")] = inner_WHILE
        def inner_method(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_method(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("m"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("m")] = inner_method
        def inner_METHOD(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_METHOD(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("M"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("M")] = inner_METHOD
        def inner_class(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_class(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("s"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("s")] = inner_class
        def inner_CLASS(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_CLASS(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("S"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("S")] = inner_CLASS
        def inner_try(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_try(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("y"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("y")] = inner_try
        def inner_except(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_except(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("x"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("x")] = inner_except
        def inner_EXCEPT(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.inner_EXCEPT(x, y)
            if scope:
                cb = default_i_callbacks.get(ord("X"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('i')][ord("X")] = inner_EXCEPT

        maps[ord('a')] = {}
        def arround_parentheses(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_parentheses(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("("), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord('(')] = arround_parentheses
        maps[ord('a')][ord(')')] = arround_parentheses
        def arround_square_brackets(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_square_brackets(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("["), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord('[')] = arround_square_brackets
        maps[ord('a')][ord(']')] = arround_square_brackets
        def arround_curly_brackets(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_curly_brackets(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("{"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord('{')] = arround_curly_brackets
        maps[ord('a')][ord('}')] = arround_curly_brackets
        def arround_greater_than(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_greater_than(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("<"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord('<')] = arround_greater_than
        maps[ord('a')][ord('>')] = arround_greater_than
        def arround_quotation(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_quotation(x, y)
            if scope:
                cb = default_a_callbacks.get(ord('"'), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord('"')] = arround_quotation
        def arround_apostrophe(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_apostrophe(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("'"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("'")] = arround_apostrophe
        def arround_backtick(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_backtick(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("`"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("`")] = arround_backtick
        def arround_word(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_word(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("w"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("w")] = arround_word
        def arround_w_o_r_d(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_w_o_r_d(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("_"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("_")] = arround_w_o_r_d
        def arround_WORD(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_WORD(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("W"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("W")] = arround_WORD

        # code objects here...
        def arround_if(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_if(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("f"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("f")] = arround_if
        def arround_IF(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_IF(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("F"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("F")] = arround_IF
        def arround_for(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_for(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("r"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("r")] = arround_for
        def arround_FOR(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_FOR(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("R"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("R")] = arround_FOR
        def arround_else(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_else(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("l"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("l")] = arround_else
        def arround_while(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_while(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("e"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("e")] = arround_while
        def arround_WHILE(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_WHILE(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("E"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("E")] = arround_WHILE
        def arround_method(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_method(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("m"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("m")] = arround_method
        def arround_METHOD(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_METHOD(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("M"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("M")] = arround_METHOD
        def arround_class(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_class(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("s"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("s")] = arround_class
        def arround_CLASS(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_CLASS(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("S"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("S")] = arround_CLASS
        def arround_try(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_try(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("y"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("y")] = arround_try
        def arround_except(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_except(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("x"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("x")] = arround_except
        def arround_EXCEPT(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_EXCEPT(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("X"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("X")] = arround_EXCEPT
        def arround_argument(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_window().buffer.arround_argument(x, y)
            if scope:
                cb = default_a_callbacks.get(ord("a"), default_callback)
                if cb is not None: return cb(scope)
        maps[ord('a')][ord("a")] = arround_argument
        maps[ord('p')] = arround_argument

    def _initialize_objects_maps(self, maps, cbs):
        self.__initialize_movement_objects_maps(maps, cbs)
        self.__initialize_inner_around_objects_maps(maps, cbs)

    def _initialize_normal_mainstream_maps(self):
        # operations
        self.maps[NORMAL][ord('c')] = {}    # change
        self.maps[NORMAL][ord('d')] = {}    # delete
        self.maps[NORMAL][ord('y')] = {}    # yank

        self.maps[NORMAL][ord('g')] = {}    # go
        self.maps[NORMAL][ord('g')][ord('c')] = {} # comment
        self.maps[NORMAL][ord('g')][ord('p')] = {} # paste
        self.maps[NORMAL][ord('>')] = {}    # indent right
        self.maps[NORMAL][ord('<')] = {}    # indent left

        self.maps[NORMAL][ord('[')] = {}
        self.maps[NORMAL][ord(']')] = {}

        # the "craft"
        def operation_movement_j(scope):
            scope.src.x = 0
            scope.dst.x = len(self.get_curr_buffer().lines[scope.dst.y]) - 2
            return scope
        def operation_movement_k(scope):
            scope.src.x = len(self.get_curr_buffer().lines[scope.src.y]) - 2
            scope.dst.x = 0
            return scope
        def operation_movement_w(scope):
            if scope.dst.y > scope.src.y:
                scope.dst.y = scope.src.y
                scope.dst.x = len(self.get_curr_window().get_line(scope.dst.y)) - 1
            scope.dst.x -= 1
            return scope
        def operation_movement_b(scope):
            scope.src.x = max(0, scope.src.x - 1)
            return scope

        # ----------------------------------------------------------------
        # change operator
        # ----------------------------------------------------------------
        def change_object_map(scope):
            self.change_begin()
            self.get_curr_window().remove_scope(scope)
            self.change_mode(INSERT, effect_change=False)
            return False
        change_object_callbacks = {}
        change_object_callbacks['default'] = change_object_map
        def change_j_map(scope):
            scope = operation_movement_j(scope)
            change_object_map(scope)
            return False
        change_object_callbacks[ord('j')] = change_j_map
        def change_k_map(scope):
            scope = operation_movement_k(scope)
            change_object_map(scope)
            return False
        change_object_callbacks[ord('k')] = change_k_map
        def change_w_map(scope):
            scope = operation_movement_w(scope)
            change_object_map(scope)
            return False
        # change_object_callbacks[ord('w')] = change_w_map # we modify it next to ce (end word)
        change_object_callbacks[ord('W')] = change_w_map
        change_object_callbacks[ord('-')] = change_w_map
        def change_b_map(scope):
            scope = operation_movement_b(scope)
            change_object_map(scope)
            return False
        change_object_callbacks[ord('b')] = change_b_map
        change_object_callbacks[ord('B')] = change_b_map
        change_object_callbacks[ord('^')] = change_b_map
        change_object_callbacks[ord('0')] = change_b_map
        self._initialize_objects_maps(self.maps[NORMAL][ord('c')], change_object_callbacks)
        # in the case of change, thw word movement is acting like the end movement.
        self.maps[NORMAL][ord('c')][ord('w')] = self.maps[NORMAL][ord('c')][ord('e')]
        self.maps[NORMAL][ord('c')][ord('W')] = self.maps[NORMAL][ord('c')][ord('E')]
        # ----------------------------------------------------------------
        # delete operator
        # ----------------------------------------------------------------
        def delete_object_map(scope):
            text = self.get_curr_buffer().get_scope_text(scope)
            if len(text) == 0: return False

            data = {}
            data['meta'] = 'char'
            data['data'] = text
            self.registers['"'] = data

            self.change_begin()
            self.get_curr_window().remove_scope(scope)
            self.change_end()
            return False
        delete_object_callbacks = {}
        delete_object_callbacks['default'] = delete_object_map
        def delete_j_map(scope):
            scope = operation_movement_j(scope)
            delete_object_map(scope)
            return False
        delete_object_callbacks[ord('j')] = delete_j_map
        def delete_k_map(scope):
            scope = operation_movement_k(scope)
            delete_object_map(scope)
            return False
        delete_object_callbacks[ord('k')] = delete_k_map
        def delete_w_map(scope):
            scope = operation_movement_w(scope)
            delete_object_map(scope)
            return False
        delete_object_callbacks[ord('w')] = delete_w_map
        delete_object_callbacks[ord('W')] = delete_w_map
        delete_object_callbacks[ord('-')] = delete_w_map
        def delete_b_map(scope):
            scope = operation_movement_b(scope)
            delete_object_map(scope)
            return False
        delete_object_callbacks[ord('b')] = delete_b_map
        delete_object_callbacks[ord('B')] = delete_b_map
        delete_object_callbacks[ord('^')] = delete_b_map
        delete_object_callbacks[ord('0')] = delete_b_map
        self._initialize_objects_maps(self.maps[NORMAL][ord('d')], delete_object_callbacks)
        # ----------------------------------------------------------------
        # yank operator
        # ----------------------------------------------------------------
        def yank_object_map(scope):
            text = self.get_curr_buffer().get_scope_text(scope)
            if len(text) == 0: return False

            # send yanked text to clipboard
            yank_to_clipboard(text)

            data = {}
            data['meta'] = 'char'
            data['data'] = text
            self.registers['"'] = data
            return False
        yank_object_callbacks = {}
        yank_object_callbacks['default'] = yank_object_map
        def yank_j_map(scope):
            scope = operation_movement_j(scope)
            yank_object_map(scope)
            return False
        yank_object_callbacks[ord('j')] = yank_j_map
        def yank_k_map(scope):
            scope = operation_movement_k(scope)
            yank_object_map(scope)
            return False
        yank_object_callbacks[ord('k')] = yank_k_map
        def yank_w_map(scope):
            scope = operation_movement_w(scope)
            yank_object_map(scope)
            return False
        yank_object_callbacks[ord('w')] = yank_w_map
        yank_object_callbacks[ord('W')] = yank_w_map
        yank_object_callbacks[ord('-')] = yank_w_map
        def yank_b_map(scope):
            scope = operation_movement_b(scope)
            yank_object_map(scope)
            return False
        yank_object_callbacks[ord('b')] = yank_b_map
        yank_object_callbacks[ord('B')] = yank_b_map
        yank_object_callbacks[ord('^')] = yank_b_map
        yank_object_callbacks[ord('0')] = yank_b_map
        self._initialize_objects_maps(self.maps[NORMAL][ord('y')], yank_object_callbacks)
        # ----------------------------------------------------------------
        # > operator
        # ----------------------------------------------------------------
        def indent_right_object_map(scope):
            self.change_begin()
            self.get_curr_window().indent_lines(scope.start.y, scope.end.y, True)
            self.change_end()
            return False
        indent_right_object_callbacks = {}
        indent_right_object_callbacks['default'] = indent_right_object_map
        self._initialize_objects_maps(self.maps[NORMAL][ord('>')], indent_right_object_callbacks)
        # ----------------------------------------------------------------
        # < operator
        # ----------------------------------------------------------------
        def indent_left_object_map(scope):
            self.change_begin()
            self.get_curr_window().indent_lines(scope.start.y, scope.end.y, False)
            self.change_end()
            return False
        indent_left_object_callbacks = {}
        indent_left_object_callbacks['default'] = indent_left_object_map
        self._initialize_objects_maps(self.maps[NORMAL][ord('<')], indent_left_object_callbacks)

        # ----------------------------------------------------------------
        # comment operator
        # ----------------------------------------------------------------
        def comment_object_map(scope):
            self.change_begin()

            try:
                comment(self, scope.start.y, scope.end.y)
            except Exception as e:
                elog(f"Exception: {e}", type="ERROR")
                elog(f"traceback: {traceback.format_exc()}", type="ERROR")

            self.change_end()
            return False
        comment_object_callbacks = {}
        comment_object_callbacks['default'] = comment_object_map
        self._initialize_objects_maps(self.maps[NORMAL][ord('g')][ord('c')], comment_object_callbacks)

        # ----------------------------------------------------------------
        # paste operator
        # ----------------------------------------------------------------
        def paste_object_map(scope):
            self.change_begin()

            self.get_curr_window().remove_scope(scope)
            data = self.registers['"']
            if data:
                if data['meta'] == 'line':
                    lines = data['data']
                    for line in reversed(lines):
                        self.get_curr_window().insert_line_before(line, propagate=False)
                    self.get_curr_buffer().flush_changes()
                elif data['meta'] == 'char':
                    lines = data['data']
                    string = '\n'.join(lines)
                    self.get_curr_window().insert_string(string)
                elif data['meta'] == 'block': pass
            self.change_end()
            return False
        paste_object_callbacks = {}
        paste_object_callbacks['default'] = paste_object_map
        self._initialize_objects_maps(self.maps[NORMAL][ord('g')][ord('p')], paste_object_callbacks)

        # ----------------------------------------------------------------
        # movements
        # ----------------------------------------------------------------
        def default_movement_cb(scope):
            self.get_curr_window().move_cursor_to_buf_location(scope.dst.x, scope.dst.y)
            return False
        normal_movement_callbacks = {}
        normal_movement_callbacks['default'] = default_movement_cb
        def j_map_cb(scope):
            number = 1
            if len(self._number) > 0:
                number = int(self._number)
            for _ in range(number): self.get_curr_window().move_down()
            return False
        normal_movement_callbacks[ord('j')] = j_map_cb
        def k_map_cb(scope):
            number = 1
            if len(self._number) > 0:
                number = int(self._number)
            for _ in range(number): self.get_curr_window().move_up()
            return False
        normal_movement_callbacks[ord('k')] = k_map_cb
        def n_map_cb(scope):
            self.get_curr_window().move_cursor_to_buf_location(scope.dst.x, scope.dst.y)
            self.get_curr_window().add_jump()
            self.get_curr_window().move_cursor_to_buf_location( scope.dst.x,
                                                                scope.dst.y)
            self.get_curr_window().add_jump()

            style = {}
            style['foreground'] = get_setting('search_highlights_foreground')
            style['background'] = get_setting('search_highlights_background')
            pattern = self.registers['/']
            self.get_curr_buffer().add_highlights("/", pattern, style)
            self.get_curr_window().draw()
            return False
        normal_movement_callbacks[ord('n')] = n_map_cb
        normal_movement_callbacks[ord('N')] = n_map_cb
        self.__initialize_movement_objects_maps(self.maps[NORMAL], normal_movement_callbacks)

        def hash_map(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_buffer().inner_word(x, y)
            pattern = self.get_curr_buffer().get_scope_text(scope)
            if len(pattern) == 0: return False
            pattern = pattern[0]
            pattern = r"((\W+)|(^))(?P<cword>"+pattern+r")\W"
            self.registers['/'] = pattern
            self._search_forward = False
            self._on_search(x, y, pattern, self._search_forward)
            return False
        self.maps[NORMAL][ord('#')] = hash_map
        def asterisk_map(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_buffer().inner_word(x, y)
            pattern = self.get_curr_buffer().get_scope_text(scope)
            if len(pattern) == 0: return False
            pattern = pattern[0]
            pattern = r"((\W+)|(^))(?P<cword>"+pattern+r")\W"
            self.registers['/'] = pattern
            self._search_forward = True
            self._on_search(x, y, pattern, self._search_forward)
            return False
        self.maps[NORMAL][ord('*')] = asterisk_map
        def slash_map(self):
            self.on_search(True)
            return False
        self.maps[NORMAL][ord('/')] = slash_map
        def question_mark_map(self):
            self.on_search(False)
            return False
        self.maps[NORMAL][ord('?')] = question_mark_map
        def tilda_map(self):
            self.change_begin()
            self.get_curr_window().upper()
            self.change_end()
            self.get_curr_window().move_right()
            return False
        self.maps[NORMAL][ord('~')] = tilda_map
        def o_map(self):
            self.change_mode(INSERT)
            self.get_curr_window().new_line_after()
            return False
        self.maps[NORMAL][ord('o')] = o_map
        def O_map(self):
            self.change_mode(INSERT)
            self.get_curr_window().new_line_before()
            return False
        self.maps[NORMAL][ord('O')] = O_map
        def A_map(self):
            self.change_mode(INSERT)
            self.get_curr_window().move_line_end()
            return False
        self.maps[NORMAL][ord('A')] = A_map
        def a_map(self):
            self.change_mode(INSERT)
            self.get_curr_window().move_right()
            return False
        self.maps[NORMAL][ord('a')] = a_map
        def I_map(self):
            self.change_mode(INSERT)
            self.get_curr_window().move_line_begin(ignore_spaces=True)
            return False
        self.maps[NORMAL][ord('I')] = I_map
        def i_map(self):
            self.change_mode(INSERT)
            return False
        self.maps[NORMAL][ord('i')] = i_map
        def s_map(self):
            self.change_begin()
            self.get_curr_window().remove_char_special(self.get_curr_window().buffer_cursor[0] + 1)
            self.change_mode(INSERT, effect_change=False)
            return False
        self.maps[NORMAL][ord('s')] = s_map
        def X_map(self):
            self.change_begin()
            self.get_curr_window().remove_char_special(self.get_curr_window().buffer_cursor[0])
            self.change_end()
            return False
        self.maps[NORMAL][ord('X')] = X_map
        def x_map(self):
            self.change_begin()
            self.get_curr_window().remove_char_special(self.get_curr_window().buffer_cursor[0] + 1)
            self.change_end()
            return False
        self.maps[NORMAL][ord('x')] = x_map
        def r_map(self):
            self.change_begin()
            self.get_curr_window().replace()
            self.change_end()
            return False
        self.maps[NORMAL][ord('r')] = r_map
        def R_map(self):
            self.change_mode(REPLACE)
            return False
        self.maps[NORMAL][ord('R')] = R_map
        def P_map(self):
            self.change_begin()
            data = self.registers['"']
            if data:
                if data['meta'] == 'line':
                    lines = data['data']
                    for line in reversed(lines):
                        self.get_curr_window().insert_line_before(line, propagate=False)
                    self.get_curr_buffer().flush_changes()
                elif data['meta'] == 'char':
                    lines = data['data']
                    string = '\n'.join(lines)
                    self.get_curr_window().insert_string(string)
                elif data['meta'] == 'block': pass
            self.change_end()
            return False
        self.maps[NORMAL][ord('P')] = P_map
        def p_map(self):
            self.change_begin()
            data = self.registers['"']
            if data:
                if data['meta'] == 'line':
                    lines = data['data']
                    for line in lines:
                        self.get_curr_window().insert_line_after(line, propagate=False)
                    self.get_curr_buffer().flush_changes()
                elif data['meta'] == 'char':
                    lines = data['data']
                    _lines = []
                    for line in lines:
                        if line.endswith('\n'):
                            _lines.append(line[:-1])
                        else:
                            _lines.append(line)
                    lines = _lines
                    string = '\n'.join(_lines)
                    self.get_curr_window().move_right()
                    self.get_curr_window().insert_string(string)
                elif data['meta'] == 'block': pass
            self.change_end()
            return False
        self.maps[NORMAL][ord('p')] = p_map
        def q_map(self):
            # TODO
            return False
        self.maps[NORMAL][ord('q')] = q_map
        def u_map(self):
            self.get_curr_window().undo()
            return False
        self.maps[NORMAL][ord('u')] = u_map
        def V_map(self):
            self.change_mode(VISUAL_LINE)
            return False
        self.maps[NORMAL][ord('V')] = V_map
        def v_map(self):
            self.change_mode(VISUAL)
            return False
        self.maps[NORMAL][ord('v')] = v_map
        def J_map(self):
            self.change_begin()
            self.get_curr_window().join_line()
            self.change_end()
            return False
        self.maps[NORMAL][ord('J')] = J_map
        def C_map(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]

            size = self.get_curr_window().get_curr_line_len()
            start_x = x
            start_y = y
            end_x = size - 2
            end_y = y

            self.change_begin()
            self.get_curr_window().remove_scope(Scope(start_x, start_y, end_x, end_y))
            self.change_mode(INSERT, effect_change=False)
            return False
        self.maps[NORMAL][ord('C')] = C_map
        def D_map(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]

            size = self.get_curr_window().get_curr_line_len()
            start_x = x
            start_y = y
            end_x = size - 2
            end_y = y

            data = {}
            data["data"] = [self.get_curr_window().get_curr_line()[start_x:end_x]]
            data["meta"] = "char"
            self.registers['"'] = data

            self.change_begin()
            self.get_curr_window().remove_scope(Scope(start_x, start_y, end_x, end_y))
            self.change_end()
            return False
        self.maps[NORMAL][ord('D')] = D_map
        def dot_map(self):
            self.screen.set_keys(self.registers['.'])
            return False
        self.maps[NORMAL][ord('.')] = dot_map

        self.maps[NORMAL][ord('z')] = {}
        def zz_map(self):
            self.get_curr_window().align_center()
            return False
        self.maps[NORMAL][ord('z')][ord('z')] = zz_map
        def zb_map(self):
            self.get_curr_window().align_bottom()
            return False
        self.maps[NORMAL][ord('z')][ord('b')] = zb_map
        def zt_map(self):
            self.get_curr_window().align_top()
            return False
        self.maps[NORMAL][ord('z')][ord('t')] = zt_map

        def yy_map(self):
            data = {}
            text = [self.get_curr_window().get_curr_line()]

            # send yanked text to clipboard
            yank_to_clipboard(text)

            data["data"] = text
            data["meta"] = "line" # to let the paste know the data is entire line.
            self.registers['"'] = data
            return False
        self.maps[NORMAL][ord('y')][ord('y')] = yy_map
        def dd_map(self):
            self.change_begin()

            data = {}
            data["data"] = [self.get_curr_window().get_curr_line()]
            data["meta"] = "line" # to let the paste know the data is entire line.
            self.registers['"'] = data

            self.get_curr_window().remove_line()
            self.change_end()
            return False
        self.maps[NORMAL][ord('d')][ord('d')] = dd_map
        def cc_map(self):
            self.change_begin()

            data = {}
            data["data"] = self.get_curr_window().get_curr_line()
            data["meta"] = "line" # to let the paste know the data is entire line.
            self.registers['"'] = data

            self.get_curr_window().empty_line(keep_whitespaces=True)
            self.change_mode(INSERT, effect_change=False)
            return False
        self.maps[NORMAL][ord('c')][ord('c')] = cc_map
        def gt_gt_map(self):
            y = self.get_curr_window().buffer_cursor[1]
            self.change_begin()
            self.get_curr_window().indent_lines(y, y, True)
            self.change_end()
            return False
        self.maps[NORMAL][ord('>')][ord('>')] = gt_gt_map
        def lt_lt_map(self):
            y = self.get_curr_window().buffer_cursor[1]
            self.change_begin()
            self.get_curr_window().indent_lines(y, y, False)
            self.change_end()
            return False
        self.maps[NORMAL][ord('<')][ord('<')] = lt_lt_map
        def gT_map(self):
            self.prev_tab()
            return False
        self.maps[NORMAL][ord('g')][ord('T')] = gT_map
        def gt_map(self):
            self.next_tab()
            return False
        self.maps[NORMAL][ord('g')][ord('t')] = gt_map
        def gf_map(self):
            line = self.get_curr_window().get_curr_line()
            line = line[self.get_curr_window().buffer_cursor[0]:]
            file_path, file_line, file_col = extract_destination(line)
            if not file_path: return False
            buffer = self.get_or_create_buffer(file_path)
            self.get_curr_window().add_jump()
            self.get_curr_window().change_buffer(buffer)
            self.get_curr_window().move_cursor_to_buf_location(file_col, file_line)
            self.get_curr_window().add_jump()
            self.get_curr_window().align_center()
            return False
        self.maps[NORMAL][ord('g')][ord('f')] = gf_map
        def gd_map(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_buffer().inner_word(x, y)
            pattern = self.get_curr_buffer().get_scope_text(scope)
            if len(pattern) == 0: return False
            pattern = pattern[0]
            pattern = r"((\W+)|(^))(?P<cword>"+pattern+r")\W"
            results = self.get_curr_buffer().search_pattern(pattern)
            if len(results) == 0: return False
            # elog(results[0])
            # start_x, start_y, end_x, end_y = results[0]
            self.get_curr_window().add_jump()
            # self.get_curr_window().move_cursor_to_buf_location(start_x, start_y)
            self.get_curr_window().move_cursor_to_buf_location(results[0].start.x, results[0].start.y)
            self.get_curr_window().add_jump()
            return False
        self.maps[NORMAL][ord('g')][ord('d')] = gd_map

        def ctrl_t_map(self):
            gotovim(self)
            if not self.get_curr_buffer().reload(force=True):
                error = ErrorPopup(self, "file changed on disk!")
                error.pop()
                self.get_curr_tab().draw() # need to redraw after popup
            return False
        self.maps[NORMAL][CTRL_T_KEY] = ctrl_t_map
        def ctrl_v_map(self):
            self.change_mode(VISUAL_BLOCK)
            return False
        self.maps[NORMAL][CTRL_V_KEY] = ctrl_v_map
        def ctrl_l_map(self):
            self.get_curr_buffer().resync_treesitter()
            self.get_curr_tab().draw()
            return False
        self.maps[NORMAL][CTRL_L_KEY] = ctrl_l_map
        def ctrl_r_map(self):
            self.get_curr_window().redo()
            return False
        self.maps[NORMAL][CTRL_R_KEY] = ctrl_r_map
        def ctrl_i_map(self):
            jump = self.get_curr_window().next_jump()
            if not jump: return False
            if jump['file_path']:
                buffer = self.get_or_create_buffer(jump['file_path'])
                if self.get_curr_buffer().id != buffer.id:
                    self.get_curr_window().change_buffer(buffer)
            elif jump['buffer_id']:
                buffer = self.get_buffer_by_id(jump['buffer_id'])
                if not buffer: return False
                if self.get_curr_buffer().id != buffer.id:
                    self.get_curr_window().change_buffer(buffer)
            else:
                return False

            self.get_curr_window().move_cursor_to_buf_location( jump['col'],
                                                                jump['line'])
            self.get_curr_window().align_center()
            return False
        self.maps[NORMAL][CTRL_I_KEY] = ctrl_i_map
        def ctrl_o_map(self):
            jump = self.get_curr_window().prev_jump()
            if not jump: return False

            if jump['file_path']:
                buffer = self.get_or_create_buffer(jump['file_path'])
                if self.get_curr_buffer().id != buffer.id:
                    self.get_curr_window().change_buffer(buffer)
            elif jump['buffer_id']:
                buffer = self.get_buffer_by_id(jump['buffer_id'])
                if not buffer: return False
                if self.get_curr_buffer().id != buffer.id:
                    self.get_curr_window().change_buffer(buffer)
            else:
                return False

            self.get_curr_window().move_cursor_to_buf_location( jump['col'],
                                                                jump['line'])
            self.get_curr_window().align_center()
            return False
        self.maps[NORMAL][CTRL_O_KEY] = ctrl_o_map

        self.maps[NORMAL][CTRL_BACKSLASH_KEY] = {}
        def ctrl_backslash_c_map(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_buffer().inner_word(x, y)
            pattern = self.get_curr_buffer().get_scope_text(scope)
            if len(pattern) == 0: return False
            pattern = f"\\W{pattern[0]}\\("

            location = rg_fzf(self, pattern)
            if location is None: return False

            file_path, file_line, file_col = extract_destination(location)
            buffer = self.get_or_create_buffer(file_path)
            self.get_curr_window().add_jump()
            self.get_curr_window().change_buffer(buffer)
            self.get_curr_window().move_cursor_to_buf_location(file_col, file_line)
            self.get_curr_window().add_jump()
            self.get_curr_window().align_center()

            # task = Task(ripgrep, pattern)
            # self.tasks.append(task)
            # def rg_on_done(results):
                # if not results:
                    # # remove the task when done.
                    # self.tasks.remove(task)
                    # return False
                # results = results.decode().splitlines()
                # if len(results) == 0:
                    # # remove the task when done.
                    # self.tasks.remove(task)
                    # return False
                # self.get_curr_window().quickfix_set(results)

                # # remove the task when done.
                # self.tasks.remove(task)
                # return True

            # task.on_done(rg_on_done)
            # task.start()
            # ret = task.wait()

            # if ret: self.get_curr_window().quickfix_pop(self.get_or_create_buffer)
            return False
        self.maps[NORMAL][CTRL_BACKSLASH_KEY][ord('c')] = ctrl_backslash_c_map
        def ctrl_backslash_s_map(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_buffer().inner_word(x, y)
            pattern = self.get_curr_buffer().get_scope_text(scope)
            if len(pattern) == 0: return False
            pattern = r"((\W+)|(^))(?P<cword>"+pattern[0]+r")\W*"

            location = rg_fzf(self, pattern)
            if location is None: return False

            file_path, file_line, file_col = extract_destination(location)
            buffer = self.get_or_create_buffer(file_path)
            self.get_curr_window().add_jump()
            self.get_curr_window().change_buffer(buffer)
            self.get_curr_window().move_cursor_to_buf_location(file_col, file_line)
            self.get_curr_window().add_jump()
            self.get_curr_window().align_center()

            # task = Task(ripgrep, pattern)
            # self.tasks.append(task)
            # def rg_on_done(results):
                # if not results:
                    # # remove the task when done.
                    # self.tasks.remove(task)
                    # return False
                # results = results.decode().splitlines()
                # if len(results) == 0:
                    # # remove the task when done.
                    # self.tasks.remove(task)
                    # return False
                # self.get_curr_window().quickfix_set(results)

                # # remove the task when done.
                # self.tasks.remove(task)
                # return True

            # task.on_done(rg_on_done)
            # task.start()
            # ret = task.wait()

            # if ret: self.get_curr_window().quickfix_pop(self.get_or_create_buffer)
            return False
        self.maps[NORMAL][CTRL_BACKSLASH_KEY][ord('s')] = ctrl_backslash_s_map
        def ctrl_close_bracket_map(self):
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            scope = self.get_curr_buffer().inner_word(x, y)
            pattern = self.get_curr_buffer().get_scope_text(scope)
            if len(pattern) == 0: return False
            pattern = pattern[0]

            results = gd(self, pattern)
            if not results: return False
            _results = results.decode('utf-8')
            _results = _results.splitlines()
            if len(_results) == 1:
                file_path, file_line, file_col = extract_destination(_results[0])
                buffer = self.get_or_create_buffer(file_path)
                self.get_curr_window().add_jump()
                self.get_curr_window().change_buffer(buffer)
                self.get_curr_window().move_cursor_to_buf_location(file_col, file_line)
                self.get_curr_window().add_jump()
                self.get_curr_window().align_center()
            else:
                self.get_curr_window().quickfix_set(_results)
                self.get_curr_window().quickfix_pop(self.get_or_create_buffer)
            return False
        self.maps[NORMAL][CTRL_CLOSE_BRACKET_KEY] = ctrl_close_bracket_map

    def _initialize_leader_maps(self):
        self.maps[NORMAL][ord(' ')] = {}        # leader
        self.maps[NORMAL][ord(' ')][ord('o')] = {} # open
        self.maps[NORMAL][ord(' ')][ord('e')] = {} # execute
        self.maps[NORMAL][ord(' ')][ord('s')] = {} # search
        self.maps[NORMAL][ord(' ')][ord('t')] = {} # treesitter
        self.maps[NORMAL][ord(' ')][ord('d')] = {} # doc
        self.maps[NORMAL][ord(' ')][ord('m')] = {} # multi-cursor
        def leader_mm_map(self):
            self.change_mode(MULTI_CURSOR_NORMAL)
            return False
        self.maps[NORMAL][ord(' ')][ord('m')][ord('m')] = leader_mm_map
        def leader_ma_map(self):
            location = self.get_curr_window().buffer_cursor
            self.get_curr_buffer().add_cursor((location[0], location[1]))
            self.get_curr_tab().draw()
            return False
        self.maps[NORMAL][ord(' ')][ord('m')][ord('a')] = leader_ma_map
        def leader_md_map(self):
            location = self.get_curr_window().buffer_cursor
            self.get_curr_buffer().del_cursor((location[0], location[1]))
            self.get_curr_tab().draw()
            return False
        self.maps[NORMAL][ord(' ')][ord('m')][ord('d')] = leader_md_map
        def leader_dl_map(self): # doc location
            doc('location', self)
            return False
        self.maps[NORMAL][ord(' ')][ord('d')][ord('l')] = leader_dl_map
        def leader_do_map(self): # doc open
            doc_path = doc_get_latest_file()
            buffer = self.get_or_create_buffer(doc_path)
            self.get_curr_tab().vsplit(buffer)
            return False
        self.maps[NORMAL][ord(' ')][ord('d')][ord('o')] = leader_do_map
        def leader_sf_map(self): # search file
            file_path = fzf(self)
            if file_path:
                buffer = self.get_or_create_buffer(file_path)
                self.get_curr_window().add_jump()
                self.get_curr_window().change_buffer(buffer)
                self.get_curr_window().add_jump()
            return False
        self.maps[NORMAL][ord(' ')][ord('s')][ord('f')] = leader_sf_map
        def leader_sc_map(self): # search content
            try:
                pattern = self.prompt("rg: ")
                if len(pattern) == 0: return False

                location = rg_fzf(self, pattern)
                if location is None: return False

                file_path, file_line, file_col = extract_destination(location)
                buffer = self.get_or_create_buffer(file_path)
                self.get_curr_window().add_jump()
                self.get_curr_window().change_buffer(buffer)
                self.get_curr_window().move_cursor_to_buf_location(file_col, file_line)
                self.get_curr_window().add_jump()
                self.get_curr_window().align_center()
            except Exception as e:
                elog(f"Exception: {e}", type="ERROR")
                elog(f"traceback: {traceback.format_exc()}", type="ERROR")
            return False
        self.maps[NORMAL][ord(' ')][ord('s')][ord('c')] = leader_sc_map
        def leader_ts_map(self): # treesitter
            abs_position = [0,0]
            window_x = self.get_curr_window().position[0]
            window_y = self.get_curr_window().position[1]
            window_cursor_x = 0
            window_cursor_y = 0
            abs_position[0] = window_x + window_cursor_x
            abs_position[1] = window_y + window_cursor_y
            try:
                ts = TreeSitterPopup(   self,
                                        self.screen,
                                        self.get_curr_buffer().treesitter,
                                        self.get_curr_window().buffer_cursor)
                node = ts.pop()
                if node:
                    y = node.start_point[0]
                    x = node.start_point[1]
                    self.get_curr_window().move_cursor_to_buf_location(x, y)
                    self.get_curr_window().align_center()

                self.get_curr_tab().draw() # need to redraw after popup
            except Exception as e:
                elog(f"Exception: {e}", type="ERROR")
                elog(f"traceback: {traceback.format_exc()}", type="ERROR")
            return False
        self.maps[NORMAL][ord(' ')][ord('t')][ord('s')] = leader_ts_map
        def leader_tf_map(self): # tree_sitter functions
            abs_position = [0,0]
            window_x = self.get_curr_window().position[0]
            window_y = self.get_curr_window().position[1]
            window_cursor_x = 0
            window_cursor_y = 0
            abs_position[0] = window_x + window_cursor_x
            abs_position[1] = window_y + window_cursor_y
            try:
                ts = TreeSitterPopup(   self,
                                        self.screen,
                                        self.get_curr_buffer().treesitter,
                                        self.get_curr_window().buffer_cursor,
                                        search_for="function")
                node = ts.pop()
                if node:
                    y = node.start_point[0]
                    x = node.start_point[1]
                    self.get_curr_window().move_cursor_to_buf_location(x, y)
                    self.get_curr_window().align_center()

                self.get_curr_tab().draw() # need to redraw after popup
            except Exception as e:
                elog(f"Exception: {e}", type="ERROR")
                elog(f"traceback: {traceback.format_exc()}", type="ERROR")
            return False
        self.maps[NORMAL][ord(' ')][ord('t')][ord('f')] = leader_tf_map
        def leader_tc_map(self): # tree_sitter class
            abs_position = [0,0]
            window_x = self.get_curr_window().position[0]
            window_y = self.get_curr_window().position[1]
            window_cursor_x = 0
            window_cursor_y = 0
            abs_position[0] = window_x + window_cursor_x
            abs_position[1] = window_y + window_cursor_y
            try:
                ts = TreeSitterPopup(   self,
                                        self.screen,
                                        self.get_curr_buffer().treesitter,
                                        self.get_curr_window().buffer_cursor,
                                        search_for="class")
                node = ts.pop()
                if node:
                    y = node.start_point[0]
                    x = node.start_point[1]
                    self.get_curr_window().move_cursor_to_buf_location(x, y)
                    self.get_curr_window().align_center()

                self.get_curr_tab().draw() # need to redraw after popup
            except Exception as e:
                elog(f"Exception: {e}", type="ERROR")
                elog(f"traceback: {traceback.format_exc()}", type="ERROR")
            return False
        self.maps[NORMAL][ord(' ')][ord('t')][ord('c')] = leader_tc_map
        def leader_p_map(self):
            text = paste_from_clipboard()
            if not text: return False
            lines = text.splitlines(keepends=True)
            self.change_begin()

            _lines = []
            for line in lines:
                if line.endswith('\n'):
                    _lines.append(line[:-1])
                else:
                    _lines.append(line)
            lines = _lines
            string = '\n'.join(_lines)
            self.get_curr_window().move_right()
            self.get_curr_window().insert_string(string)

            self.change_end()
            return False
        self.maps[NORMAL][ord(' ')][ord('p')] = leader_p_map
        def leader_P_map(self):
            details = DetailsPopup(self)
            details.pop()
            self.get_curr_tab().draw() # need to redraw after popup
            return False
        self.maps[NORMAL][ord(' ')][ord('P')] = leader_P_map
        def leader_oc_map(self):
            config_path = os.path.expanduser('~/.config/editor/config.json')
            buffer = self.get_or_create_buffer(config_path)
            self.get_curr_tab().vsplit(buffer)
            return False
        # open config
        self.maps[NORMAL][ord(' ')][ord('o')][ord('c')] = leader_oc_map
        def leader_r_map(self):
            text = self.prompt("replace: ")
            if len(text) == 0: return False
            last_pattern = self.registers['/']
            if not last_pattern or len(last_pattern) == 0: return False

            start = self.get_curr_buffer().get_file_x_y(0)
            if not start: return False
            start_x, start_y = start

            end_pos = len(self.get_curr_buffer().get_file_stream()) - 1
            end = self.get_curr_buffer().get_file_x_y(end_pos)
            if not end: return False
            end_x, end_y = end

            self.change_begin()
            self.get_curr_window().search_replace_scope(Scope(start_x, start_y, end_x, end_y),
                                                        last_pattern,
                                                        text)
            self.change_end()
            return False
        # replace editor pattern
        self.maps[NORMAL][ord(' ')][ord('r')] = leader_r_map
        def leader_i_map(self):
            self.get_curr_window().buffer_cursor[1]
            lines = LinesPopup( self,
                                self.screen,
                                self.get_curr_buffer().lines,
                                self.get_curr_window().buffer_cursor[1])
            y = lines.pop()
            self.get_curr_window().move_cursor_to_buf_location(0, y)

            self.get_curr_tab().draw() # need to redraw after popup
            return False
        self.maps[NORMAL][ord(' ')][ord('i')] = leader_i_map
        def leader_l_map(self):
            self.get_curr_window().quickfix_pop(self.get_or_create_buffer)
            return False
        self.maps[NORMAL][ord(' ')][ord('l')] = leader_l_map
        def leader_j_map(self):
            self.get_curr_window().quickfix_next(self.get_or_create_buffer)
            return False
        self.maps[NORMAL][ord(' ')][ord('j')] = leader_j_map
        def leader_k_map(self):
            self.get_curr_window().quickfix_prev(self.get_or_create_buffer)
            return False
        self.maps[NORMAL][ord(' ')][ord('k')] = leader_k_map
        def leader_ec_map(self):
            load_settings()
            return False
        # reload settings of editor ([e]xecute [c]onfig (legacy))
        self.maps[NORMAL][ord(' ')][ord('e')][ord('c')] = leader_ec_map

    def _initialize_normal_maps(self):
        def colon_map(self):
            return self.on_command()
        self.maps[NORMAL][ord(':')] = colon_map

        self._initialize_normal_mainstream_maps()
        self._initialize_normal_window_maps()
        self._initialize_leader_maps()

    def _initialize_insert_ctrl_maps(self):
        self.maps[INSERT][CTRL_X_KEY] = {}
        def ctrl_w_map(self):
            window = self.get_curr_window()
            start_x, start_y = window.buffer_cursor[0] - 1, window.buffer_cursor[1]
            ret = window.buffer.find_prev_word(start_x, start_y)
            if not ret: return
            end_x, end_y = ret

            window.remove_scope(Scope(end_x, end_y, start_x, start_y))
            self.get_curr_window().draw_cursor()
            return False
        self.maps[INSERT][CTRL_W_KEY] = ctrl_w_map
        def ctrl_n_map(self):
            ret = self.generate_word_completion_options()
            if not ret: return False
            x, options = ret
            if len(options) == 0: return False
            if len(options) == 1:
                self.get_curr_window().insert_string(options[0][1])
                return False

            window_x = self.get_curr_window().content_position[0]
            window_y = self.get_curr_window().content_position[1]
            buf_y = self.get_curr_window().buffer_cursor[1]

            abs_position = [0,0]
            expanded_x = self.get_curr_window()._expanded_x(buf_y, x)
            abs_position[0] = window_x + expanded_x
            abs_position[1] = window_y + self.get_curr_window().window_cursor[1]

            completion = CompletionPopup(   self,
                                            self.screen,
                                            position=abs_position,
                                            options=options)
            choise = completion.pop()
            self.get_curr_tab().draw() # need to redraw after completion

            if choise: self.get_curr_window().insert_string(choise[1])
            return False
        self.maps[INSERT][CTRL_N_KEY] = ctrl_n_map
        def ctrl_xf_map(self):
            ret = self.generate_path_completion_options()
            if not ret: return False
            x, options = ret
            if len(options) == 0: return False
            if len(options) == 1:
                self.get_curr_window().insert_string(options[0][1])
                return False

            window_x = self.get_curr_window().content_position[0]
            window_y = self.get_curr_window().content_position[1]
            buf_y = self.get_curr_window().buffer_cursor[1]

            abs_position = [0,0]
            expanded_x = self.get_curr_window()._expanded_x(buf_y, x)
            abs_position[0] = window_x + expanded_x
            abs_position[1] = window_y + self.get_curr_window().window_cursor[1]

            completion = CompletionPopup(   self,
                                            self.screen,
                                            position=abs_position,
                                            options=options)
            choise = completion.pop()
            self.get_curr_tab().draw() # need to redraw after completion

            if choise:
                self.get_curr_window().insert_string(choise[1])
            return False
        self.maps[INSERT][CTRL_X_KEY][ord('f')] = ctrl_xf_map
        self.maps[INSERT][CTRL_X_KEY][CTRL_F_KEY] = ctrl_xf_map

    def _initialize_insert_maps(self):
        self._initialize_insert_ctrl_maps()

    def _initialize_visual_block_maps(self):
        pass
        # # def visual_object_map(scope):
            # # start_x, start_y, end_x, end_y = scope

            # # self.get_curr_buffer().visual_set_scope(start_x, start_y, end_x, end_y)
            # # self.get_curr_window().move_cursor_to_buf_location(end_x, end_y)

            # # self.draw()
            # # return False
        # # self.__initialize_inner_around_objects_maps(self.maps[VISUAL_BLOCK], visual_object_map)
        # def d_map(self):
            # # scope = self.get_curr_buffer().visual_get_scope()
            # # if not scope: return False
            # # self.change_begin()

            # # start_x, start_y, end_x, end_y = scope
            # # self.get_curr_window().remove_scope(start_x, start_y, end_x, end_y)

            # # self.change_end()

            # # self.change_mode(NORMAL)
            # return False
        # self.maps[VISUAL_BLOCK][ord('d')] = d_map
        # def p_map(self):
            # # scope = self.get_curr_buffer().visual_get_scope()
            # # if not scope: return False
            # # start_x, start_y, end_x, end_y = scope

            # # self.change_begin()

            # # self.get_curr_window().remove_scope(start_x, start_y, end_x, end_y)
            # # data = self.registers['"']
            # # if data:
                # # if data['meta'] == 'line':
                    # # lines = data['data']
                    # # for line in reversed(lines):
                        # # self.get_curr_window().insert_line_before(line, propagate=False)
                    # # self.get_curr_buffer().flush_changes()
                # # elif data['meta'] == 'char':
                    # # lines = data['data']
                    # # string = '\n'.join(lines)
                    # # self.get_curr_window().insert_string(string)
                # # elif data['meta'] == 'block': pass

            # # self.change_end()

            # # self.change_mode(NORMAL)
            # return False
        # self.maps[VISUAL_BLOCK][ord('p')] = p_map
        # def c_map(self):
            # # scope = self.get_curr_buffer().visual_get_scope()
            # # if not scope: return False
            # # self.change_begin()

            # # start_x, start_y, end_x, end_y = scope
            # # self.get_curr_window().remove_scope(start_x, start_y, end_x, end_y)

            # # self.change_mode(INSERT, effect_change=False)
            # return False
        # self.maps[VISUAL_BLOCK][ord('c')] = c_map
        # def y_map(self):
            # # scope = self.get_curr_buffer().visual_get_scope()
            # # if not scope: return False

            # # start_x, start_y, end_x, end_y = scope
            # # text = self.get_curr_buffer().get_scope_text(start_x, start_y, end_x, end_y)
            # # if len(text) == 0: return False

            # # # send yanked text to clipboard
            # # yank_to_yank_to_clipboard(text)

            # # data = {}
            # # data['meta'] = 'char'
            # # data['data'] = text
            # # self.registers['"'] = data

            # # self.change_mode(NORMAL)
            # return False
        # self.maps[VISUAL_BLOCK][ord('y')] = y_map
        # def j_map(self):
            # self.get_curr_window()._move_down()
            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord('j')] = j_map
        # def k_map(self):
            # self.get_curr_window()._move_up()
            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord('k')] = k_map
        # def l_map(self):
            # self.get_curr_window()._move_right()
            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord('l')] = l_map
        # def h_map(self):
            # self.get_curr_window()._move_left()
            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord('h')] = h_map
        # def w_map(self):
            # self.get_curr_window().move_word_forward()
            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord('w')] = w_map
        # def W_map(self):
            # self.get_curr_window().move_WORD_forward()
            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord('W')] = W_map
        # def e_map(self):
            # self.get_curr_window().move_word_end()
            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord('e')] = e_map
        # def E_map(self):
            # self.get_curr_window().move_WORD_end()
            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord('E')] = E_map
        # def b_map(self):
            # self.get_curr_window().move_word_backward()
            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord('b')] = b_map
        # def f_map(self):
            # try:
                # char = self.get_curr_window().find()
                # self._action = 'f'
                # self._char = char

                # x = self.get_curr_window().buffer_cursor[0]
                # y = self.get_curr_window().buffer_cursor[1]
                # self.get_curr_buffer().visual_set_current(x, y)
                # self.draw()
            # except Exception as e:
                # elog(f"Exception: {e}", type="ERROR")
                # elog(f"traceback: {traceback.format_exc()}", type="ERROR")
            # return False
        # self.maps[VISUAL_BLOCK][ord('f')] = f_map
        # def F_map(self):
            # char = self.get_curr_window().find_back()
            # self._action = 'F'
            # self._char = char

            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord('F')] = F_map
        # def t_map(self):
            # char = self.get_curr_window().till()
            # self._action = 't'
            # self._char = char

            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord('t')] = t_map
        # def T_map(self):
            # char = self.get_curr_window().till_back()
            # self._action = 'T'
            # self._char = char

            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord('T')] = T_map
        # def semicolon_map(self):
            # if self._action == 'f':
                # self.get_curr_window()._find(self._char)
            # if self._action == 'F':
                # self.get_curr_window()._find_back(self._char)
            # if self._action == 't':
                # self.get_curr_window()._till(self._char)
            # if self._action == 'T':
                # self.get_curr_window()._till_back(self._char)

            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord(';')] = semicolon_map
        # def comma_map(self):
            # if self._action == 'f':
                # self.get_curr_window()._find_back(self._char)
            # if self._action == 'F':
                # self.get_curr_window()._find(self._char)
            # if self._action == 't':
                # self.get_curr_window()._till_back(self._char)
            # if self._action == 'T':
                # self.get_curr_window()._till(self._char)

            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord(',')] = comma_map
        # def dollar_map(self):
            # self.get_curr_window().move_line_end()
            # x = self.get_curr_window().buffer_cursor[0]
            # y = self.get_curr_window().buffer_cursor[1]
            # self.get_curr_buffer().visual_set_current(x, y)
            # self.draw()
            # return False
        # self.maps[VISUAL_BLOCK][ord('$')] = dollar_map

    def _initialize_visual_line_maps(self):
        self.maps[VISUAL_LINE][ord(' ')] = {} # leader
        self.maps[VISUAL_LINE][ord(' ')][ord('d')] = {} # doc
        self.maps[VISUAL_LINE][ord(' ')][ord('d')][ord('c')] = None # doc code
        self.maps[VISUAL_LINE][ord(' ')][ord('d')][ord('n')] = None # doc note
        def d_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False

            lines = []
            for y in range(scope.start.y, scope.end.y + 1):
                lines.append(self.get_curr_buffer().lines[y])

            self.change_begin()
            for y in reversed(range(scope.start.y, scope.end.y + 1)):
                self.get_curr_window().remove_line_at(y, propagate=False)
            self.get_curr_buffer().flush_changes()

            self.change_end()

            # send yanked text to clipboard
            yank_to_clipboard(lines)

            data = {}
            data['meta'] = 'line'
            data['data'] = lines
            self.registers['"'] = data

            self.change_mode(NORMAL)
            return False
        self.maps[VISUAL_LINE][ord('d')] = d_map
        def c_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False

            lines = []
            for y in range(scope.start.y, scope.end.y + 1):
                lines.append(self.get_curr_buffer().lines[y])

            self.change_begin()
            for y in reversed(range(scope.start.y, scope.end.y)):
                self.get_curr_window().remove_line_at(y, propagate=False)
            self.get_curr_buffer().flush_changes()
            self.get_curr_window().empty_line(keep_whitespaces=True)

            data = {}
            data['meta'] = 'line'
            data['data'] = lines
            self.registers['"'] = data

            self.change_mode(INSERT)
            return False
        self.maps[VISUAL_LINE][ord('c')] = c_map
        def y_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False

            lines = []
            for y in range(scope.start.y, scope.end.y + 1):
                lines.append(self.get_curr_buffer().lines[y])
            if len(lines) == 0: return False

            # send yanked text to clipboard
            yank_to_clipboard(lines)

            data = {}
            data['meta'] = 'line'
            data['data'] = lines
            self.registers['"'] = data

            self.change_mode(NORMAL)
            return False
        self.maps[VISUAL_LINE][ord('y')] = y_map
        def p_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False

            lines = []
            for y in range(scope.start.y, scope.end.y + 1):
                lines.append(self.get_curr_buffer().lines[y])

            self.change_begin()
            # remove current lines
            for y in reversed(range(scope.start.y, scope.end.y + 1)):
                self.get_curr_window().remove_line_at(y, propagate=False)
            self.get_curr_buffer().flush_changes()

            self.get_curr_window().move_up()

            # paste yanked data
            data = self.registers['"']
            if data:
                if data['meta'] == 'line':
                    lines = data['data']
                    for line in lines:
                        self.get_curr_window().insert_line_after(line, propagate=False)
                    self.get_curr_buffer().flush_changes()
                elif data['meta'] == 'char':
                    lines = data['data']
                    _lines = []
                    for line in lines:
                        if line.endswith('\n'):
                            _lines.append(line[:-1])
                        else:
                            _lines.append(line)
                    lines = _lines
                    string = '\n'.join(lines)
                    self.get_curr_window().move_right()
                    self.get_curr_window().insert_string(string)
                elif data['meta'] == 'block': pass

            self.change_end()

            self.change_mode(NORMAL)
            return False
        self.maps[VISUAL_LINE][ord('p')] = p_map

        def visual_line_movements_object_map(scope):
            self.get_curr_window().move_cursor_to_buf_location(scope.dst.x, scope.dst.y)
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            self.get_curr_buffer().visual_set_current(x, y)
            self.draw()
            return False
        visual_line_movement_object_callbacks = {}
        visual_line_movement_object_callbacks['default'] = visual_line_movements_object_map
        self.__initialize_movement_objects_maps(self.maps[VISUAL_LINE], visual_line_movement_object_callbacks)

        def gq_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False

            scope.start.x = 0
            scope.end.x = len(self.get_curr_window().get_line(scope.end.y)) - 2

            self.get_curr_window().move_cursor_to_buf_location(scope.start.x, scope.start.y)
            self.change_begin()
            try:
                format(self, scope)
            except Exception as e:
                elog(f"Exception: {e}", type="ERROR")
                elog(f"traceback: {traceback.format_exc()}", type="ERROR")
            self.change_end()

            self.change_mode(NORMAL)
            return False
        self.maps[VISUAL_LINE][ord('g')][ord('q')] = gq_map
        def gc_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False
            self.change_begin()

            try:
                comment(self, scope.start.y, scope.end.y)
            except Exception as e:
                elog(f"Exception: {e}", type="ERROR")
                elog(f"traceback: {traceback.format_exc()}", type="ERROR")

            self.change_end()

            self.change_mode(NORMAL)
            return False
        self.maps[VISUAL_LINE][ord('g')][ord('c')] = gc_map
        self.maps[VISUAL_LINE][ord('>')] = {}
        self.maps[VISUAL_LINE][ord('<')] = {}
        def lt_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False
            self.change_begin()
            self.get_curr_window().indent_lines(scope.start.y, scope.end.y, False)
            self.change_end()
        self.maps[VISUAL_LINE][ord('<')] = lt_map
        def gt_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False
            self.change_begin()
            self.get_curr_window().indent_lines(scope.start.y, scope.end.y, True)
            self.change_end()
            return False
        self.maps[VISUAL_LINE][ord('>')] = gt_map
        def leader_r_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False
            # Xs are matter in this case, so make them right
            scope.start.x = 0
            scope.end.x = len(self.get_curr_window().get_line(scope.end.y)) - 1

            text = self.prompt("replace: ")
            if len(text) == 0: return False
            last_pattern = self.registers['/']
            if not last_pattern or len(last_pattern) == 0: return False

            self.change_begin()
            self.get_curr_window().search_replace_scope(scope,
                                                        last_pattern,
                                                        text)
            self.change_end()
            self.change_mode(NORMAL)
            return False
        self.maps[VISUAL_LINE][ord(' ')][ord('r')] = leader_r_map
        def leader_dc_map(self):
            doc('code', self)
            self.change_mode(NORMAL)
            return False
        self.maps[VISUAL_LINE][ord(' ')][ord('d')][ord('c')] = leader_dc_map
        def leader_dn_map(self):
            doc('note', self)
            self.change_mode(NORMAL)
            return False
        self.maps[VISUAL_LINE][ord(' ')][ord('d')][ord('n')] = leader_dn_map

    def _initialize_visual_maps(self):
        def visual_inner_arround_object_map(scope):
            self.get_curr_buffer().visual_set_scope(scope)
            self.get_curr_window().move_cursor_to_buf_location(scope.end.x, scope.end.y)
            self.draw()
            return False
        visual_inner_arround_object_callbacks = {}
        visual_inner_arround_object_callbacks['default'] = visual_inner_arround_object_map
        self.__initialize_inner_around_objects_maps(self.maps[VISUAL], visual_inner_arround_object_callbacks)
        def visual_movements_object_map(scope):
            self.get_curr_window().move_cursor_to_buf_location(scope.dst.x, scope.dst.y)
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            self.get_curr_buffer().visual_set_current(x, y)
            self.draw()
            return False
        visual_movement_object_callbacks = {}
        visual_movement_object_callbacks['default'] = visual_movements_object_map
        self.__initialize_movement_objects_maps(self.maps[VISUAL], visual_movement_object_callbacks)

        def d_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False

            text = self.get_curr_buffer().get_scope_text(scope)
            if len(text) == 0: return False

            data = {}
            data['meta'] = 'char'
            data['data'] = text
            self.registers['"'] = data

            # send yanked text to clipboard
            yank_to_clipboard(text)

            self.change_begin()

            self.get_curr_window().remove_scope(scope)

            self.change_end()

            self.change_mode(NORMAL)
            return False
        self.maps[VISUAL][ord('d')] = d_map
        def p_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False

            self.change_begin()

            self.get_curr_window().remove_scope(scope)
            data = self.registers['"']
            if data:
                if data['meta'] == 'line':
                    lines = data['data']
                    for line in reversed(lines):
                        self.get_curr_window().insert_line_before(line, propagate=False)
                    self.get_curr_buffer().flush_changes()
                elif data['meta'] == 'char':
                    lines = data['data']
                    _lines = []
                    for line in lines:
                        if line.endswith('\n'):
                            _lines.append(line[:-1])
                        else:
                            _lines.append(line)
                    lines = _lines
                    string = '\n'.join(lines)
                    self.get_curr_window().insert_string(string)
                elif data['meta'] == 'block': pass

            self.change_end()

            self.change_mode(NORMAL)
            return False
        self.maps[VISUAL][ord('p')] = p_map
        def c_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False
            self.change_begin()

            self.get_curr_window().remove_scope(scope)

            self.change_mode(INSERT, effect_change=False)
            return False
        self.maps[VISUAL][ord('c')] = c_map
        def y_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False

            text = self.get_curr_buffer().get_scope_text(scope)
            if len(text) == 0: return False

            # send yanked text to clipboard
            yank_to_clipboard(text)

            data = {}
            data['meta'] = 'char'
            data['data'] = text
            self.registers['"'] = data

            self.change_mode(NORMAL)
            return False
        self.maps[VISUAL][ord('y')] = y_map

        def slash_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False

            text = self.get_curr_buffer().get_scope_text(scope)
            if len(text) == 0: return False
            text = re.escape(text[0])

            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            self.change_mode(NORMAL)
            self.registers['/'] = text
            self._search_forward = True
            self._on_search(x, y, text, self._search_forward)
            return False
        self.maps[VISUAL][ord('/')] = slash_map
        def question_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False

            text = self.get_curr_buffer().get_scope_text(scope)
            if len(text) == 0: return False
            text = text[0]

            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            self.change_mode(NORMAL)
            self.registers['/'] = text
            self._search_forward = False
            self._on_search(x, y, text, self._search_forward)
            return False
        self.maps[VISUAL][ord('?')] = question_map

        # leader maps
        self.maps[VISUAL][ord(' ')] = {}

        def leader_s_c_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False

            text = self.get_curr_buffer().get_scope_text(scope)
            if len(text) == 0: return False
            pattern = text[0]

            location = rg_fzf(self, pattern)
            if location is None: return False

            self.change_mode(NORMAL)

            file_path, file_line, file_col = extract_destination(location)
            buffer = self.get_or_create_buffer(file_path)
            self.get_curr_window().add_jump()
            self.get_curr_window().change_buffer(buffer)
            self.get_curr_window().move_cursor_to_buf_location(file_col, file_line)
            self.get_curr_window().add_jump()
            self.get_curr_window().align_center()

            # task = Task(ripgrep, text)
            # self.tasks.append(task)
            # def rg_on_done(results):
                # if not results: return
                # self.get_curr_tab().split(Buffer(data_in_bytes=results))

                # # remove the task when done.
                # self.tasks.remove(task)

            # task.on_done(rg_on_done)
            # task.start()

            return False
        self.maps[VISUAL][ord(' ')][ord('s')] = {}
        self.maps[VISUAL][ord(' ')][ord('s')][ord('c')] = leader_s_c_map
        def leader_r_map(self):
            scope = self.get_curr_buffer().visual_get_scope()
            if not scope: return False

            text = self.prompt("replace: ")
            if len(text) == 0: return False
            last_pattern = self.registers['/']
            if not last_pattern or len(last_pattern) == 0: return False

            self.change_begin()
            self.get_curr_window().search_replace_scope(scope,
                                                        last_pattern,
                                                        text)
            self.change_end()
            self.change_mode(NORMAL)
            return False
        self.maps[VISUAL][ord(' ')][ord('r')] = leader_r_map

    def __foreach_cursor(self, cb):
        buf = self.get_curr_buffer()

        local_cursors = buf.cursors.copy()

        buf_index = 0
        for i, (x, y) in enumerate(local_cursors):
            ret = cb(self, buf, x, y)

            # remove cursor
            if ret is None:
                buf.cursors.pop(buf_index)
                continue

            # update cursor if need be
            buf.cursors[buf_index] = ret
            buf_index += 1

    def _initialize_multi_cursor_insert_maps(self):
        pass
    def _initialize_multi_cursor_normal_maps(self):
        def w_map(self):
            def _w_map(self, buffer, x, y):
                ret = buffer.find_next_word(x, y)
                if not ret: return x, y
                return ret
            self.__foreach_cursor(_w_map)
            self.get_curr_tab().draw()
            return False
        self.maps[MULTI_CURSOR_NORMAL][ord('w')] = w_map
        def i_map(self):
            self.change_mode(MULTI_CURSOR_INSERT)
            return False
        self.maps[MULTI_CURSOR_NORMAL][ord('i')] = i_map

    def initialize_maps(self):
        self._initialize_normal_maps()
        self._initialize_insert_maps()
        self._initialize_visual_maps()
        self._initialize_visual_line_maps()
        self._initialize_visual_block_maps()
        self._initialize_multi_cursor_normal_maps()
        self._initialize_multi_cursor_insert_maps()

    def initialize_registers(self):
        # we dont add all of vim's registers for now..
        self.registers = {}
        self.internal_registers = {}

        # named registers
        for char in "abcdefghijklmnopqrstuvwxyz": self.registers[char] = None
        for char in "ABCDEFGHIJKLMNOPQRSTUVWXYZ": self.registers[char] = None
        # numbered registers
        for num in "0123456789": self.registers[num] = None
        # unamed register
        self.registers['"'] = None
        # last search pattern register
        self.registers['/'] = None
        # last change register
        self.registers['.'] = []
        self.internal_registers['.'] = []

    def __init__(self, screen):
        self.screen = screen
        self.screen.set_cursor_block_blink() # default for normal mode

        self.height, self.width = screen.get_height(), screen.get_width()
        Hooks.register(ON_RESIZE, self.screen_resize_handler)

        self.initialize_registers()
        self._number = ''
        self._action = 'f' # options are 'f','F','t','T'
        self._char = None
        self._search_forward = True

        self._replace_line = ""
        self._replace_x = -1
        self._replace_y = -1

        self.maps = {}
        self.maps[NORMAL] = {}
        self.maps[INSERT] = {}
        self.maps[VISUAL] = {}
        self.maps[VISUAL_LINE] = {}
        self.maps[VISUAL_BLOCK] = {}
        self.maps[REPLACE] = {}
        self.maps[MULTI_CURSOR_NORMAL] = {}
        self.maps[MULTI_CURSOR_INSERT] = {}

        self.initialize_maps()

        # start in normal mode
        self.mode = NORMAL
        self.curr_maps = self.maps[self.mode]

        self.tabs = []
        self.windows = []
        self.buffers = []
        self.tasks = []

        self.curr_tab = -1

        # Register to global events!
        Hooks.register(ON_BUFFER_CREATE_AFTER, self.on_buffer_create_after_callback)
        Hooks.register(ON_BUFFER_DESTROY_AFTER, self.on_buffer_destroy_after_callback)
        Hooks.register(ON_KEY, self.on_key_callback)

    def get_or_create_buffer(self, file_path):
        for buf in self.buffers:
            if buf.file_path == os.path.abspath(file_path):
                return buf
        return Buffer(file_path)
    def get_buffer_by_id(self, buffer_id):
        for buf in self.buffers:
            if buf.id == buffer_id:
                return buf
        return None

    def _create_tab(self, buffer=None):
        self.tabs.append(Tab(self.screen, self.width, self.height, buffer))
        self.get_curr_tab().hide()
        self.curr_tab = len(self.tabs) - 1
        self.get_curr_tab().show()

        self.get_curr_tab().draw()
        return self.get_curr_tab()

    def next_tab(self):
        self.get_curr_tab().hide()
        self.curr_tab = (self.curr_tab + 1) % len(self.tabs)
        self.get_curr_tab().show()
        self.get_curr_tab().draw()

    def prev_tab(self):
        self.get_curr_tab().hide()
        self.curr_tab = (self.curr_tab - 1) % len(self.tabs)
        self.get_curr_tab().show()
        self.get_curr_tab().draw()

    def get_curr_tab(self):
        return self.tabs[self.curr_tab]
    def get_curr_window(self):
        return self.get_curr_tab().get_curr_window()
    def get_curr_buffer(self):
        return self.get_curr_window().buffer

    def bootstrap(self):
        global args
        global pending_buffer

        if not args.filename:
            buffer = Buffer(data_in_bytes=pending_buffer)
            self._create_tab(buffer)
        else:
            file = args.filename[0]

            buffer = self.get_or_create_buffer(file)
            self._create_tab(buffer)

    def screen_resize_handler(self, size):
        self.width, self.height = size
        self.get_curr_tab().resize(self.width, self.height)
        self.get_curr_tab().draw()

    def _quit_command(self):
        tab = self.get_curr_tab()
        window = tab.get_curr_window()

        if len(tab.windows) > 1:
            tab.close_window(window)
            return False
        if len(self.tabs) == 1:
            tab.close()
            return True

        to_delete = self.tabs.pop(self.curr_tab)
        self.curr_tab = self.curr_tab % len(self.tabs)
        to_delete.close()
        self.get_curr_tab().draw()
        return False

    def exec_command(self, command):
        cmd = command.split()[0]
        args = command.split()[1:] if len(command.split()) > 1 else None
        force = cmd.endswith('!')
        # remove the '!'
        cmd = cmd[:-1] if force else cmd

        if cmd == 'e':
            if not args:
                if not self.get_curr_buffer().reload(force=force):
                    error = ErrorPopup(self, "file changed on disk!")
                    error.pop()
                    self.get_curr_tab().draw() # need to redraw after popup
            else:
                # TODO:
                pass
            return False
        if cmd == 'w':
            if not self.get_curr_buffer().write(force=force):
                error = ErrorPopup(self, "file changed on disk!")
                error.pop()
                self.get_curr_tab().draw() # need to redraw after popup
            return False
        if cmd == 'q':
            if not force and self.get_curr_buffer().file_changed_on_disk():
                error = ErrorPopup(self, "file changed on disk!")
                error.pop()
                self.get_curr_tab().draw() # need to redraw after popup
                return False
            if not force and self.get_curr_buffer().is_there_local_change():
                error = ErrorPopup(self, "file changed on buffer!")
                error.pop()
                self.get_curr_tab().draw() # need to redraw after popup
                return False
            return self._quit_command()
        if cmd == 'wq':
            if not self.get_curr_buffer().write(force=force):
                error = ErrorPopup(self, "file changed on disk!")
                error.pop()
                self.get_curr_tab().draw() # need to redraw after popup
                return False
            return self._quit_command()
        if cmd == 'qa':
            for buf in self.buffers:
                if not force and buf.file_changed_on_disk():
                    error = ErrorPopup(self, "file changed on disk!")
                    error.pop()
                    self.get_curr_tab().draw() # need to redraw after popup
                    return False
                if not force and buf.is_there_local_change():
                    error = ErrorPopup(self, "file changed on buffer!")
                    error.pop()
                    self.get_curr_tab().draw() # need to redraw after popup
                    return False
            return True
        if cmd == 'wqa':
            for buf in self.buffers:
                if not buf.write(force=force):
                    error = ErrorPopup(self, "file changed on disk!")
                    error.pop()
                    self.get_curr_tab().draw() # need to redraw after popup
                    return False
            return True

        try:
            line_num = int(command)
            curr_x = self.get_curr_window().buffer_cursor[0]
            self.get_curr_window().move_cursor_to_buf_location(curr_x, line_num - 1)
        except: pass
        return False

    def draw_command(self, command):
        style = {}
        style['background'] = get_setting('status_line_background')
        style['foreground'] = get_setting('status_line_foreground')

        command_position = [0, 0]
        command_position[1] = int(self.height - 1)
        command_length = self.width

        self.screen.write(  command_position[1],
                            command_position[0],
                            command.ljust(command_length),
                            style)
        self.screen.move_cursor(    command_position[1],
                                    command_position[0] + len(command))

    def on_replace(self, key):
        cur_x = self.get_curr_window().buffer_cursor[0]
        cur_y = self.get_curr_window().buffer_cursor[1]
        if key == BACKSPACE_KEY:
            if cur_y == self._replace_y and cur_x == self._replace_x:
                return False
            if cur_y > self._replace_y:
                self.get_curr_window().remove_char()
                return False
            if cur_x > len(self._replace_line) - 1:
                self.get_curr_window().remove_char()
                return False
            prev_char = self._replace_line[cur_x - 1]
            self.get_curr_window().replace_char_backward(prev_char)
            return False

        if key == TAB_KEY:
            tab = get_setting("tab_insert")
            return False

        try:
            char = chr(key)
            if char in printable:
                if cur_x == len(self.get_curr_window().get_curr_line()) - 1:
                    self.get_curr_window().insert_char(char)
                else:
                    self.get_curr_window().replace_char_forward(char)
            else:
                elog(f"REPLACE: ({key}) not printable.")
        except Exception as e:
            elog(f"Exception: {e}", type="ERROR")
            elog(f"traceback: {traceback.format_exc()}", type="ERROR")
        return False

    def on_multi_insert(self, key):
        def _single_insert(self, buffer, x, y):
            elog(f"key: {key}")
            ret_x, ret_y = x, y
            if key == BACKSPACE_KEY:
                return ret_x, ret_y

            if key == TAB_KEY:
                # expand tab to spaces
                ret_x, ret_y = buffer.insert_string(x, y, get_setting("tab_insert"))
                return ret_x, ret_y

            try:
                char = chr(key)
                elog(f"MULTI_CURSOR_INSERT: ({key}) -> {char}")
                if char in printable:
                    ret_x, ret_y = buffer.insert_string(x, y, char)
                else:
                    elog(f"INSERT: ({key}) not printable.")
            except Exception as e: elog(f"[!] on_multi_insert: {e}")
            return ret_x, ret_y

        self.__foreach_cursor(_single_insert)
        self.get_curr_tab().draw()
        return False

    def on_insert(self, key):
        ret = False

        if key == BACKSPACE_KEY:
            line = self.get_curr_window().get_curr_line()
            x = self.get_curr_window().buffer_cursor[0]
            if line[x-4:x] == '    ':
                self.get_curr_window().remove_chars(4)
            else:
                self.get_curr_window().remove_char()

            return ret

        if key == TAB_KEY:
            # expand tab to spaces
            self.get_curr_window().insert_string(get_setting("tab_insert"))
            return ret

        try:
            char = chr(key)
            if char in printable:
                self.get_curr_window().insert_char(char)
            else:
                elog(f"INSERT: ({key}) not printable.")
        except Exception as e:
            elog(f"Exception: {e}", type="ERROR")
            elog(f"traceback: {traceback.format_exc()}", type="ERROR")
        return ret

    def _find_closest_match(self, x, y, matches, forward=True):
        if forward:
            for scope in matches:
                if scope.start.y < y: continue
                if scope.start.y == y and scope.start.x <= x: continue
                return (scope.start.x, scope.start.y)
            # wrap to start
            return matches[0].start.x, matches[0].start.y
        else:
            for scope in reversed(matches):
                if scope.start.y > y: continue
                if scope.start.y == y and scope.start.x >= x: continue
                return (scope.start.x, scope.start.y)
            # wrap to end
            return matches[-1].start.x, matches[-1].start.y

    def _on_search(self, x, y, pattern, forward, add_to_jumplist=False):
        results = self.get_curr_buffer().search_pattern(pattern)
        if len(results) == 0: return False

        pos = self._find_closest_match(x, y, results, forward)
        if not pos: return False

        if add_to_jumplist: self.get_curr_window().add_jump()
        self.get_curr_window().move_cursor_to_buf_location( pos[0],
                                                            pos[1])
        if add_to_jumplist: self.get_curr_window().add_jump()

        style = {}
        style['foreground'] = get_setting('search_highlights_foreground')
        style['background'] = get_setting('search_highlights_background')

        self.get_curr_buffer().add_highlights("/", pattern, style)
        self.get_curr_window().draw()
        return True

    def prompt(self, ask=None, on_change=None):
        text = ""
        to_return = ""
        while True:
            if ask: self.draw_command(f"{ask}{text}")
            else: self.draw_command(f"{text}")

            key = self.screen.get_key()

            if key == ENTER_KEY:
                to_return = text
                break
            if key == ESC_KEY: break
            if key == BACKSPACE_KEY:
                if len(text) > 0:
                    text = text[:-1]
                    if on_change: on_change(text)
            else:
                try:
                    char = chr(key)
                    if char in printable:
                        text += char
                        if on_change: on_change(text)
                except: continue
        self.get_curr_tab().draw()
        return to_return

    def on_search(self, forward):
        origin_x = self.get_curr_window().buffer_cursor[0]
        origin_y = self.get_curr_window().buffer_cursor[1]
        success = False
        def on_change(pattern):
            nonlocal success
            success = self._on_search(origin_x, origin_y, pattern, forward)
        pattern = self.prompt("/" if forward else "?", on_change)

        if len(pattern) > 0 and success:
            self.registers['/'] = pattern
            self._search_forward = forward
        else:
            self.get_curr_window().add_jump()
            self.get_curr_window().move_cursor_to_buf_location( origin_x,
                                                                origin_y)
            self.get_curr_window().add_jump()
            self.get_curr_buffer().clear_highlights()
            self.get_curr_window().draw()

    def on_command(self):
        command = self.prompt(":")
        if len(command) == 0: return False
        return self.exec_command(command)

    def on_key(self, key):
        # enter number mode
        if self.mode == NORMAL or self.mode == VISUAL_LINE:
            self._number = ''
            if ord('1') <= key <= ord('9'):
                while ord('0') <= key <= ord('9'):
                    self._number += chr(key)
                    key = self.screen.get_key()

        # dot functionality, recording.
        if self.mode == NORMAL and self.curr_maps == self.maps[self.mode]:
            self.internal_registers["."] = [key]

        if key == ESC_KEY:
            if self.mode == MULTI_CURSOR_INSERT:
                self.change_mode(MULTI_CURSOR_NORMAL)
                return False

            self.change_mode(NORMAL)
            return False

        if key in self.curr_maps:
            if callable(self.curr_maps[key]):
                func = self.curr_maps[key]
                # if we reached the level where we have a callable, that means
                # we return to top level of the mappings
                self.curr_maps = self.maps[self.mode]
                return func(self)

            if isinstance(self.curr_maps[key], dict):
                # this means we need to keep nesting
                self.curr_maps = self.curr_maps[key]
                return False

            # We reached a dead-end. start from the top again in normal
            # mode.
            self.change_mode(NORMAL)
            return False
        # If we have no mappings matches, it is only find under insert-mode
        # where we free to input free text.
        elif self.mode == INSERT:
            return self.on_insert(key)
        elif self.mode == REPLACE:
            return self.on_replace(key)
        elif self.mode == MULTI_CURSOR_INSERT:
            return self.on_multi_insert(key)

        # We reached a dead-end. start from the top again in normal
        # mode.
        self.change_mode(NORMAL)
        return False

    def generate_word_completion_options(self):
        options = []

        try:
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            start_x = x

            words = []
            for buf in self.buffers:
                words.extend(re.findall(r'\w+', buf.get_file_stream()))
            if len(words) == 0: return None

            line = self.get_curr_window().get_curr_line()
            if re.match(r'\s', line[x - 1]):
                options = [(option, option) for option in words]
                start_x = x
            else:
                ret = self.get_curr_buffer().find_prev_word(x, y)
                if not ret: return None

                start_x, start_y = ret
                curr_word = line[start_x:x]
                for word in words:
                    if word.startswith(curr_word) and word != curr_word:
                        options.append((word, word[len(curr_word):]))
            return (start_x, list(set(options)))
        except Exception as e:
            elog(f"Exception: {e}", type="ERROR")
            elog(f"traceback: {traceback.format_exc()}", type="ERROR")
        return None

    def generate_path_completion_options(self):
        options = []
        curr_WORD = ""

        try:
            x = self.get_curr_window().buffer_cursor[0]
            y = self.get_curr_window().buffer_cursor[1]
            start_x = x

            line = self.get_curr_window().get_curr_line()
            if re.match(r'\s', line[x - 1]):
                start_x = x
            else:
                ret = self.get_curr_buffer().find_prev_WORD(x, y)
                if not ret: return None
                start_x, start_y = ret
                curr_WORD = line[start_x:x]

            start_pos, options = find_files_suggestions(start_x, curr_WORD)
            return (start_pos, options)
        except Exception as e:
            elog(f"Exception: {e}", type="ERROR")
            elog(f"traceback: {traceback.format_exc()}", type="ERROR")
        return None

def stdin_pending():
    import termios
    import fcntl
    import array
    import os

    global pending_buffer

    stdin = 0
    size = array.array('i', [0])
    fcntl.ioctl(stdin, termios.FIONREAD, size)
    size = size[0]
    if size > 0:
        pending_buffer = os.read(stdin, size)

def main():
    global args

    parser = argparse.ArgumentParser()
    parser.add_argument('filename', nargs='*')
    args = parser.parse_args()

    try:
        stdin_pending()
        screen = Screen()
        editor = Editor(screen)
        editor.bootstrap()
    except Exception as e:
        elog(f"Exception: {e}", type="ERROR")
        elog(f"traceback: {traceback.format_exc()}", type="ERROR")
        return

    k = 0
    while True:
        try:
            to_exit = editor.on_key(k)
            if to_exit: break
        except Exception as e:
            elog(f"Exception: {e}", type="ERROR")
            elog(f"traceback: {traceback.format_exc()}", type="ERROR")

            error_text = f"Exception: {e}\n"
            error_text += f"traceback: {traceback.format_exc()}"
            error = ErrorPopup(editor, error_text)
            error.pop()
            editor.get_curr_tab().draw() # need to redraw after popup

        k = screen.get_key()

    screen.clear()
    screen.move_cursor(0,0)


if __name__ == "__main__":
    # import cProfile
    # with cProfile.Profile() as profile:
        main()
    # profile.dump_stats("/tmp/stats.csv")

