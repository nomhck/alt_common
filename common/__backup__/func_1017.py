# encoding: utf-8

import sys
sys.path.append('..')
import pandas as pd
import numpy as np
import datetime
from common.util import targets


class transfer_iter():
    # 初期化
    def __init__(self, _df_act, _df_pln, _brand_list=None, _calc_date=None):
        self.df_act = _df_act
        self.df_pln = _df_pln

        # Formatting
        self.df_act.date = pd.to_datetime(self.df_act.date)
        self.df_pln.date = pd.to_datetime(self.df_pln.date)
        self.df_pln.waku_no = self.df_pln.waku_no.astype(str)

        if _brand_list is not None:
            self.brand_list_ = _brand_list
        else:
            self.brand_list_ = self.df_act.brand.unique()
            print('| List of brands: {}'.format(self.brand_list_))

        # for b in self.brand_list_:
        #     print('|', b)

        if _calc_date is not None:
            self.calc_date_ = datetime.datetime.strptime(_calc_date, "%Y/%m/%d")
        else:
            self.calc_date_ = self.df_act.date.max()
            self.calc_date_ = datetime.datetime.strptime(self.calc_date_, "%Y/%m/%d")
            print('| Setting calculation date with {}'.format(self.calc_date_))


    # 達成率を計算する関数
    def calc_achive_rate(self):
        self.ach_dict_ = {}
        self.avg_ach_rt_ = 0.0
        a_, b_ = 0, 0

        for b in self.brand_list_:
            grp_act_ = self.df_act.loc[(self.df_act.target == '世帯') * (self.df_act.brand == b), 'actual_grp'].sum()
            grp_pln_ = self.df_pln.loc[(self.df_pln.target == '世帯') * (self.df_pln.brand == b) * (self.df_pln.date > self.calc_date_), 'plan_grp'].sum()
            grp_init_ = self.df_pln.loc[(self.df_pln.target == '世帯') * (self.df_pln.brand == b), 'buy_grp'].sum()
            ach_rt_ = (grp_act_ + grp_pln_) / grp_init_
            self.ach_dict_[b] = ach_rt_
            a_ += grp_act_ + grp_pln_
            b_ += grp_init_
            # print('|', b, round(ach_rt_ * 100, 1))

        # 最大達成率・最小達成率のブランドを特定します
        self.max_brand_ = max(self.ach_dict_)
        self.min_brand_ = min(self.ach_dict_)

        # 平均値を計算します
        self.avg_ach_rt_ = a_ / b_

        return self.ach_dict_, self.avg_ach_rt_


    #　平均からの誤差の閾値超過を検証
    def validation(self, _threshold=0.05):
        self.threshold_ = _threshold
        self.volatility_ = []
        self.validation_ = None

        for k, v in self.ach_dict_.items():
            print('| - {} {} ({})'.format(k, round(v * 100, 1), round((v - self.avg_ach_rt_) * 100, 1)))
            self.volatility_.append(v - self.avg_ach_rt_)

        self.vol_max_ = max(self.volatility_)
        self.vol_min_ = min(self.volatility_)
        self.vol_range_ = max(self.volatility_) - min(self.volatility_)
        self.validation_ = 'OK' if self.vol_range_ < self.threshold_ else 'NG'

        print('| MAX: {}, MIN: {}, RANGE: {}, VALIDATION: {}'.format(
            round(self.vol_max_ * 100, 1),
            round(self.vol_min_ * 100, 1),
            round(self.vol_range_ * 100, 1),
            self.validation_))

        return self.validation_


    #　ターゲット含有率の計算
    def calc_content_rate(self):

        print('| Brand with max achive rate: {}, its target: {}'.format(self.max_brand_, targets[self.max_brand_]))

        self.cont_rt_ = {}
        self.waku_max_ = None

        #　最大達成率のブランドに絞る
        df_max_brand = self.df_pln.loc[(self.df_pln.brand == self.max_brand_), ['target','brand','waku_no','plan_grp']]

        self.waku_list_ = df_max_brand.waku_no.unique()

        df_max_brand_fam = df_max_brand.loc[df_max_brand.target == '世帯',]
        df_max_brand_tar = df_max_brand.loc[df_max_brand.target == targets[self.max_brand_],]

        # ブランド変更前の当該ブランドのターゲット含有率
        try:
            self.cont_rt_['all'] = df_max_brand_tar.loc[:,'plan_grp'].sum() / df_max_brand_fam.loc[:,'plan_grp'].sum()
        except:
            # 計算できない場合最大値１とする
            self.cont_rt_['all'] = 1.0

        # 各枠を除いた場合における当該ブランドのターゲット含有率
        for i, w in enumerate(self.waku_list_):
            self.cont_rt_.setdefault(w,'')
            try:
                self.cont_rt_[w] = df_max_brand_tar.loc[df_max_brand_tar.waku_no != w, 'plan_grp'].sum() \
                    / df_max_brand_fam.loc[df_max_brand_fam.waku_no != w,'plan_grp'].sum()
            except:
                self.cont_rt_[w] = 1.0

            # 当該ブランドのターゲット含有率が最も保守的（最大）となるときに除外した枠Noを見つける
            if i == 0:
                self.waku_max_ = w
            elif self.cont_rt_[w] > self.cont_rt_[self.waku_max_] and w is not 'all':
                self.waku_max_ = w

        # 並べ替え
        self.cont_rt_ = dict(sorted(self.cont_rt_.items(), key=lambda x:x[0]))

        return self.cont_rt_, self.waku_max_


    # ブランド変更
    def replace_brand(self, _replace=False):

        print('| Replacing brand on {} ({} -> {})'.format(self.waku_max_, self.max_brand_, self.min_brand_))

        # calc_content_rate で算出した「枠」に対して、ブランドを「達成率が最小」のブランドに変更する：最大ブランド → 最小ブランド
        self.df_pln_wk = self.df_pln.copy()
        self.df_pln_wk.loc[(self.df_pln_wk.brand == self.max_brand_) * (self.df_pln_wk.waku_no == self.waku_max_), 'brand'] \
            = self.min_brand_

        return self.df_pln_wk
