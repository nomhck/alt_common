# encoding: utf-8

import sys
sys.path.append('..')
import pandas as pd
import numpy as np
import datetime
from common.util import targets


class transfer_iter():
    # 初期化
    def __init__(self, _df_buy, _df_act, _df_pln, _calc_date=None, _calc_factor=None, _atime_flag=None, _verbose=False):

        self.verbose_ = _verbose
        self.calc_factor_ = _calc_factor
        self.atime_flag_ = _atime_flag

        # Deep Copy
        self.df_act = _df_act.copy()
        self.df_pln = _df_pln.copy()
        self.df_buy = _df_buy.copy()

        if self.atime_flag_ == 'Aタイムなし':
            self.df_pln = self.df_pln.loc[self.df_pln.timerank != 'A',]
            self.df_buy = self.df_buy.loc[self.df_buy.timerank != 'A',]

        # Data Type Formatting
        self.df_act.date = pd.to_datetime(self.df_act.date)
        self.df_pln.date = pd.to_datetime(self.df_pln.date)
        self.df_buy.date = pd.to_datetime(self.df_buy.date)
        self.df_pln.waku_no = self.df_pln.waku_no.astype(str)
        self.df_buy.waku_no = self.df_buy.waku_no.astype(str)

        if _calc_date is not None:
            self.calc_date_ = datetime.datetime.strptime(_calc_date, "%Y/%m/%d")
        else:
            self.calc_date_ = self.df_act.date.max()
            self.calc_date_ = datetime.datetime.strptime(self.calc_date_, "%Y/%m/%d")

            if self.verbose_ is True:
                print('| Set calculation date with {}'.format(self.calc_date_))

        # 計算結果カラムの追加
        if len(self.df_pln.columns) == 16:
            self.df_pln['timing'] = self.calc_factor_
            self.df_pln['atime_flag'] = self.atime_flag_
            self.df_pln['brand_before'] = self.df_pln.brand
            self.df_pln['brand_after'] = self.df_pln.brand

        # ブランドリスト、1Wスキップ期間も含む   /////////// 前後いれかえ ////////////
        self.brand_list_ = self.df_pln.brand_after.unique()

        # 予測GRPデータによる達成率の計算には7日間の準備期間を含める
        # self.df_pln = self.df_pln.loc[self.df_pln.date > self.calc_date_,]////////////


        # if self.verbose is True:
        #     print('| List of brands: {}'.format(self.brand_list_))


    # ブランドごとの達成率を計算する関数、要素は世帯GRPベースで、達成率（％）＝（実績GRP＋予測GRP）/（買付GRP）
    # 実績GRP : from self.df_act（1週目終了後、2週目終了後のそれぞれのアクチュアル）
    # 予測GRP : from self.df_pln（ブランド変更のたびにブランド情報を再帰的に更新する）
    # 買付GRP : from self.df_buy（初期時点の買付GRP）
    def calc_achive_rate(self):
        self.ach_dict_ = {}
        self.avg_ach_rt_ = 0.0
        a_, b_ = 0, 0

        # 達成率の計算には1W飛ばさない'df_pln'を使う
        for i, b in enumerate(self.brand_list_):
            grp_act_ = self.df_act.loc[(self.df_act.target == '世帯') * (self.df_act.brand == b), 'actual_grp'].sum()
            grp_pln_ = self.df_pln.loc[(self.df_pln.target == '世帯') * (self.df_pln.brand_after == b), 'plan_grp'].sum()
            grp_buy_ = self.df_buy.loc[(self.df_buy.target == '世帯') * (self.df_buy.brand == b), 'buy_grp'].sum()

            try:
                self.ach_dict_[b] = (grp_act_ + grp_pln_) / grp_buy_
                a_ += grp_act_ + grp_pln_
                b_ += grp_buy_
            except:
                self.ach_dict_[b] = 0

            # a_ += grp_act_ + grp_pln_
            # b_ += grp_buy_

            # 最大達成率のブランド
            if i == 0:
                self.max_brand_ = b
            elif self.ach_dict_[b] > self.ach_dict_[self.max_brand_]:
                self.max_brand_ = b

            # 最小達成率のブランド
            if i == 0:
                self.min_brand_ = b
            elif self.ach_dict_[b] < self.ach_dict_[self.min_brand_]:
                self.min_brand_ = b

        # 最大達成率・最小達成率のブランドを特定します(この方法ではうまくいかない…)
        # self.max_brand_ = max(self.ach_dict_)
        # self.min_brand_ = min(self.ach_dict_)

        # self.ach_dict_['max_brand'] = self.max_brand_
        # self.ach_dict_['min_brand'] = self.min_brand_
        # self.ach_dict_['max_target'] = targets[self.max_brand_]

        # 平均値を計算します（不変です）
        try:
            self.avg_ach_rt_ = a_ / b_
        except:
            self.avg_ach_rt_ = 0

        return self


    #　平均からの誤差の閾値超過を検証
    def validation(self, _threshold=0.05):
        self.threshold_ = _threshold
        self.volatility_ = []
        self.validation_ = None

        for k, v in self.ach_dict_.items():
            vol = v - self.avg_ach_rt_
            self.volatility_.append(vol)

            if self.verbose_ is True:
                print('| - {} {} ({})'.format(k, round(v * 100, 1), round(vol * 100, 1)))

        self.vol_max_ = max(self.volatility_)
        self.vol_min_ = min(self.volatility_)
        self.vol_range_ = self.vol_max_ - self.vol_min_
        self.validation_ = 'OK' if self.vol_range_ < self.threshold_ else 'NG'

        print('| AVG ACH: {}, VOL_MAX: {}, VOL_MIN: {}, RANGE: {}, VALID: {}'.format(
            round(self.avg_ach_rt_ * 100, 1),
            round(self.vol_max_ * 100, 1),
            round(self.vol_min_ * 100, 1),
            round(self.vol_range_ * 100, 1),
            self.validation_))

        return self


    #　ターゲット含有率の計算
    def calc_content_rate(self):

        if self.verbose_ is True:
            print('| Brand with max achive rate: {} (target: {})'.format(self.max_brand_, targets[self.max_brand_]))

        self.cont_rt_ = {}
        self.waku_max_ = None

        #　最大達成率のブランドに絞る。ブランド変更の対象期間は計算基準日から1W後以降
        skip_1w = self.df_pln.date > self.calc_date_ + datetime.timedelta(days=7)
        max_brd = self.df_pln.brand_after == self.max_brand_

        df_mb = self.df_pln.loc[skip_1w * max_brd, ['target','brand_after','waku_no','plan_grp']]

        waku_list = df_mb.waku_no.unique()
        waku_list = ["0122","0124"]

        df_mb_fam = df_mb.loc[df_mb.target == '世帯',]
        df_mb_tar = df_mb.loc[df_mb.target == targets[self.max_brand_],]

        try:
            # ブランド変更前の当該ブランドのターゲット含有率
            self.cont_rt_['all'] = df_mb_tar.loc[:,'plan_grp'].sum() / df_mb_fam.loc[:,'plan_grp'].sum()
        except:
            # 計算できない場合最大値１とする
            self.cont_rt_['all'] = 1.0

        # 各枠を除いた場合における当該ブランドのターゲット含有率
        for i, w in enumerate(waku_list):
            try:
                self.cont_rt_[w] = df_mb_tar.loc[df_mb_tar.waku_no != w, 'plan_grp'].sum() \
                    / df_mb_fam.loc[df_mb_fam.waku_no != w, 'plan_grp'].sum()
            except:
                self.cont_rt_[w] = 1.0

            # 当該ブランドのターゲット含有率が最も保守的（最大）となるときに除外した枠Noを見つける
            if i == 0:
                self.waku_max_ = w
            elif self.cont_rt_[w] > self.cont_rt_[self.waku_max_]:
                self.waku_max_ = w

        # 並べ替え
        # self.cont_rt_ = dict(sorted(self.cont_rt_.items(), key=lambda x:x[0]))

        return self.max_brand_, self.waku_max_, self.cont_rt_[self.waku_max_]


    # ブランド変更
    def replace_brand(self, _replace=False):

        if self.verbose_ is True:
            print('| We should replace the brand on {} ({} -> {})'.format(self.waku_max_, self.max_brand_, self.min_brand_))

        # calc_content_rate で算出した「枠」に対して、ブランドを「達成率が最小」のブランドに変更する：最大ブランド → 最小ブランド
        self.df_pln_wk = self.df_pln.copy()

        # 変更対象レコードの特定
        skip_1w = self.df_pln_wk.date > self.calc_date_ + datetime.timedelta(days=7)
        max_brd = self.df_pln_wk.brand_after == self.max_brand_
        max_wak = self.df_pln_wk.waku_no == self.waku_max_
        ref_flg = skip_1w * max_brd * max_wak

        self.df_pln_wk.loc[ref_flg, 'brand_after'] = self.min_brand_
        # ブランド変更の対象になるのは1W飛ばし部分
        # if ref_flg is True:
        #     self.df_pln_wk.loc[ref_flg, 'brand_after'] = self.min_brand_
        # else:
        #     print('| There is not waku that should be replaced.')

        return self.df_pln_wk, ref_flg
