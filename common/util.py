# encoding: utf-8

import sys
sys.path.append('..')

targets = {
    'リポビタンD': 'M1',
    'パブロンメディカル': 'M2',
    'ヴィックスドロップ': 'F1',
    '大正漢方胃腸薬': 'M2',
    'リアップX5プラス': 'M3',
}

brands = {
    'リポビタンD': 'Lipovitan D',
    'パブロンメディカル': 'Pabron Medical',
    'ヴィックスドロップ': 'Vicks Vapodrops',
    '大正漢方胃腸薬': 'Taisho Kampo',
    'リアップX5プラス': 'Riup X5 Plus',
}

fname_getter = {
    '1週目終了後': 'week1',
    '2週目終了後': 'week2',
}