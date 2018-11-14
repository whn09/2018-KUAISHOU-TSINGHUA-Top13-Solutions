# 该特征工程 滑窗步长为1天，全量数据，无部分平均加权

from multiprocessing import Pool
import numpy as np
import pandas as pd
from pandas import DataFrame as DF
import gc
from multiprocessing import Pool
from sklearn.preprocessing import LabelEncoder
import time
from scipy import stats


def get_transform(now, start_date, end_date):
    get_trans = now[(now['day'] >= start_date) & (now['day'] <= end_date)]
    return get_trans


def get_label(start_date, end_date):
    merge_name = ['user_id', 'day']
    all_log = pd.concat([action_log[merge_name], app_log[merge_name], video_log[merge_name]], axis=0)
    train_label = get_transform(all_log, start_date, end_date)
    train_1 = DF(list(set(train_label['user_id']))).rename(columns={0: 'user_id'})
    train_1['label'] = 1
    reg_temp = get_transform(register_log, 1, start_date - 1)
    train_1 = train_1[train_1['user_id'].isin(reg_temp['user_id'])]
    train_0 = DF(list(set(reg_temp['user_id']) - set(train_1['user_id']))).rename(columns={0: 'user_id'})
    train_0['label'] = 0
    del train_label
    gc.collect()
    return pd.concat([train_1, train_0], axis=0)


def check_id(uid, now):
    return now[now['user_id'].isin(uid)]


def get_mode(now):
    return stats.mode(now)[0][0]


def get_binary_seq(now, start_date, end_date):
    day = list(range(1, end_date - start_date + 2))
    day.reverse()
    ans1 = 0
    binary_day = []
    now_uni = now.unique()
    for i in day:
        if i in now_uni:
            binary_day.append(1)
        else:
            binary_day.append(0)
    return binary_day


def get_binary1(now, start_date, end_date):  # Boss Feature
    ans = 0
    binary_day = get_binary_seq(now, start_date, end_date)
    for i in range(len(binary_day)):
        ans += binary_day[i] * (2 ** i)
    return ans


def get_binary2(now, start_date, end_date):  # Boss Feature
    ans = 0
    binary_day = get_binary_seq(now, start_date, end_date)
    for i in range(len(binary_day)):
        ans += binary_day[i] * (1 / (end_date - i))
    return ans


def get_time_log_weight_sigma(now, start_date, end_date):
    window_len = end_date + 1 - start_date
    ans = np.zeros(window_len)
    sigma_ans = 0
    for i in now:
        ans[(i - 1) % window_len] += 1
    for i in range(window_len):
        if ans[i] != 0:
            sigma_ans += np.log(ans[i] / (window_len - i))
    return sigma_ans


def get_max_count(x, x_max):
    x_max = int(x_max)
    if x_max > 0:
        return x['day'].value_counts()[x_max]
    else:
        return 0


def get_max_movie(x, x_max):
    x_max = int(x_max)
    if x_max > 0:
        x = x[x['day'] == x_max]
        return x['video_id'].nunique()
    else:
        return 0


def get_type_feature(control, name, now, train_data, start_date, end_date, gap, gap_name):
    now = get_transform(now, start_date, end_date)

    train_data = pd.merge(train_data,
                          now.groupby(['user_id']).apply(lambda x: (end_date - x[name].max())).reset_index().rename(
                              columns={0: 'max1_' + control + name + gap_name}).fillna(-1), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: (end_date - get_second_day(x[name], 2))).reset_index().rename(
        columns={0: 'max2_' + control + name + gap_name}).fillna(end_date - start_date), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: get_max_count(x, np.nan_to_num(x['day'].max()))).reset_index().rename(
        columns={0: 'max_count_' + control + name + gap_name}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: get_max_count(x, get_second_day(x[name], 2))).reset_index().rename(
        columns={0: 'max2_count_' + control + name + gap_name}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].nunique()).reset_index().rename(
        columns={0: 'nunique_' + control + name + gap_name}).fillna(0), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: get_max_movie(x, np.nan_to_num(x['day'].max()))).reset_index().rename(
        columns={0: 'nunique_video_' + control + name + gap_name}).fillna(0), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: get_max_movie(x, get_second_day(x[name], 2))).reset_index().rename(
        columns={0: 'nunique2_video_' + control + name + gap_name}).fillna(0), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: (x[name].max() - get_second_day(x[name], 2))).reset_index().rename(
        columns={0: 'max_distance_12_' + control + name + str(end_date - start_date)}).fillna(end_date - start_date),
                          on=['user_id'], how='left')

    return train_data


def get_encoder_feature(control, name, now, train_data, start_date, end_date):
    now = get_transform(now, start_date, end_date)

    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: get_binary1(x[name], start_date, end_date)).reset_index().rename(
        columns={0: 'encoder1_01seq' + control + name + '_' + str(end_date - start_date)}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: get_binary2(x[name], start_date, end_date)).reset_index().rename(
        columns={0: 'encoder2_01seq' + control + name + '_' + str(end_date - start_date)}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: get_time_log_weight_sigma(x[name], start_date, end_date)).reset_index().rename(
        columns={0: 'LogSigma_' + control + name + '_' + str(end_date - start_date)}), on=['user_id'], how='left')

    return train_data


def get_time_feature(control, name, now, train_data, start_date, end_date):
    now = get_transform(now, start_date, end_date)

    # 描述性统计特征 6
    t1 = time.time()
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].nunique()).reset_index().rename(
        columns={0: 'nunique_all_' + control + name + str(end_date - start_date)}).fillna(0), on=['user_id'],
                          how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].count()).reset_index().rename(
        columns={0: 'count_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')
    #print(control, name, now, train_data, start_date, end_date)
    print('train_data.keys():', train_data.keys())
    train_data['nunique / count' + control + name + str(end_date - start_date)] = train_data[
                                                                                      'nunique_all_' + control + name + str(
                                                                                          end_date - start_date)] / \
                                                                                  train_data[
                                                                                      'count_' + control + name + str(
                                                                                          end_date - start_date)]
    train_data = pd.merge(train_data,
                          now.groupby(['user_id']).apply(lambda x: (x[name].min() - start_date)).reset_index().rename(
                              columns={0: 'min-start_' + control + name + str(end_date - start_date)}), on=['user_id'],
                          how='left')
    train_data = pd.merge(train_data,
                          now.groupby(['user_id']).apply(lambda x: (end_date - x[name].min())).reset_index().rename(
                              columns={0: 'end-min_' + control + name + str(end_date - start_date)}), on=['user_id'],
                          how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].kurt()).reset_index().rename(
        columns={0: 'kurt_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].skew()).reset_index().rename(
        columns={0: 'skew_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')
    train_data = pd.merge(train_data,
                          now.groupby(['user_id']).apply(lambda x: x[name].quantile(q=0.84)).reset_index().rename(
                              columns={0: 'q4_' + control + name + str(end_date - start_date)}), on=['user_id'],
                          how='left')
    train_data = pd.merge(train_data,
                          now.groupby(['user_id']).apply(lambda x: x[name].quantile(q=0.92)).reset_index().rename(
                              columns={0: 'q5_' + control + name + str(end_date - start_date)}), on=['user_id'],
                          how='left')
    train_data = pd.merge(train_data,
                          now.groupby(['user_id']).apply(lambda x: x[name].quantile(q=0.97)).reset_index().rename(
                              columns={0: 'q6_' + control + name + str(end_date - start_date)}), on=['user_id'],
                          how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: get_mode(x[name])).reset_index().rename(
        columns={0: 'mode_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')

    t2 = time.time()
    print(name, ' Describe Finished... ', t2 - t1, ' Shape: ', train_data.shape)

    t1 = time.time()
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: abs(np.var(np.fft.fft(x[name])))).reset_index().rename(
        columns={0: 'fft_var_' + control + name + str(end_date - start_date)}).fillna(-1), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: abs(np.mean(np.fft.fft(x[name])))).reset_index().rename(
        columns={0: 'fft_mean_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: abs(np.var(np.fft.fft(get_binary_seq(x[name], start_date, end_date))))).reset_index().rename(
        columns={0: 'fft_01seq_var_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: abs(np.mean(np.fft.fft(get_binary_seq(x[name], start_date, end_date))))).reset_index().rename(
        columns={0: 'fft_01seq_mean_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')
    t2 = time.time()
    print(control, ' FFT Finished...', t2 - t1, ' Shape: ', train_data.shape)

    t1 = time.time()
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: np.array(get_binary_seq(x[name], start_date, end_date)).std()).reset_index().rename(
        columns={0: '01seq_std_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: np.array(get_binary_seq(x[name], start_date, end_date)).mean()).reset_index().rename(
        columns={0: '01seq_mean_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')
    t2 = time.time()
    print(control, ' 01seq Describe Finished... ', t2 - t1, ' Shape: ', train_data.shape)

    # 时间衰减 4
    t1 = time.time()
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: get_binary1(x[name], start_date, end_date)).reset_index().rename(
        columns={0: 'encoder1_01seq' + control + name + '_' + str(end_date - start_date)}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: get_binary2(x[name], start_date, end_date)).reset_index().rename(
        columns={0: 'encoder2_01seq' + control + name + '_' + str(end_date - start_date)}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: get_time_log_weight_sigma(x[name], start_date, end_date)).reset_index().rename(
        columns={0: 'LogSigma_' + control + name + '_' + str(end_date - start_date)}), on=['user_id'], how='left')
    t2 = time.time()
    print(control, ' Sigma Finished... ', t2 - t1, ' Shape: ', train_data.shape)

    t1 = time.time()
    train_data = pd.merge(train_data,
                          now.groupby(['user_id']).apply(lambda x: (end_date - x[name].max())).reset_index().rename(
                              columns={0: 'max1_' + control + name + str(end_date - start_date)}).fillna(
                              end_date - start_date), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: (end_date - get_second_day(x[name], 2))).reset_index().rename(
        columns={0: 'max2_' + control + name + str(end_date - start_date)}).fillna(end_date - start_date),
                          on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: (end_date - get_second_day(x[name], 3))).reset_index().rename(
        columns={0: 'max3_' + control + name + str(end_date - start_date)}).fillna(end_date - start_date),
                          on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(
        lambda x: (x[name].max() - get_second_day(x[name], 2))).reset_index().rename(
        columns={0: 'max_distance_12_' + control + name + str(end_date - start_date)}).fillna(end_date - start_date),
                          on=['user_id'], how='left')

    t2 = time.time()

    print(control, ' Max Finished... ', t2 - t1, ' Shape: ', train_data.shape)

    return train_data


def get_second_day(now, seq):
    now = list(now.unique())
    for i in range(seq - 1):
        if len(now) > 1:
            now.remove(max(now))
        else:
            return 0
    return max(now)


def get_id_feature(control, name, now, train_data, start_date, end_date):
    now = get_transform(now, start_date, end_date)

    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].count()).reset_index().rename(
        columns={0: 'count_' + control + name + str(end_date - start_date)}).fillna(0), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].nunique()).reset_index().rename(
        columns={0: 'nunique_' + control + name + str(end_date - start_date)}).fillna(0), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].var()).reset_index().rename(
        columns={0: 'var_' + control + name + str(end_date - start_date)}).fillna(0), on=['user_id'], how='left')

    return train_data


def get_diff_feature(control, name, now, train_data, start_date, end_date):
    now = get_transform(now, start_date, end_date)

    t1 = time.time()
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].count()).reset_index().rename(
        columns={0: 'count_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].nunique()).reset_index().rename(
        columns={0: 'nunique_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].std()).reset_index().rename(
        columns={0: 'var_' + control + name + str(end_date - start_date)}).fillna(-1), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].mean()).reset_index().rename(
        columns={0: 'mean_' + control + name + str(end_date - start_date)}).fillna(-1), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].max()).reset_index().rename(
        columns={0: 'max_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: get_mode(x[name])).reset_index().rename(
        columns={0: 'mode_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')
    train_data = pd.merge(train_data, now.groupby(['user_id']).apply(lambda x: x[name].min()).reset_index().rename(
        columns={0: 'min_' + control + name + str(end_date - start_date)}), on=['user_id'], how='left')
    t2 = time.time()
    print(control, ' Get Diff Feature Finished... Used: ', t2 - t1, ' Shape: ', train_data.shape)
    return train_data


def HowManyPeopleWatch(df):
    num_people = len(df['user_id'].unique())
    return num_people


def MostHandle(df):
    most_handle = df.groupby('video_id').size().max()
    return most_handle


def FavAuthorCreate(df):
    most_author = df.groupby('author_id').size().sort_values(ascending=False).index[0]
    create_video_num = len(df[df['author_id'] == most_author]['video_id'].unique())
    watch_other_video_num = len(df[df['author_id'] == most_author]['video_id'].unique())
    watch_other_video = 1 if watch_other_video_num > 1 else 0
    return create_video_num, watch_other_video


def GongXianDu(df):
    d11 = df.set_index('video_id')
    d11['gongxian_rate'] = df.groupby('video_id').size()
    d11['gongxian_rate'] = d11['gongxian_rate'] / d11['video_watched_times']
    meand = d11['gongxian_rate'].mean()
    sumd = d11['gongxian_rate'].sum()
    stdd = d11['gongxian_rate'].std()
    skeww = d11['gongxian_rate'].skew()
    kurtt = d11['gongxian_rate'].kurt()
    return sumd, meand, stdd, skeww, kurtt


def get_category_count(name, deal_now, train_data, start_date, end_date):
    count = DF(deal_now.groupby(['user_id', name]).size().reset_index().rename(columns={0: 'times'}))
    count_size = deal_now.groupby([name]).size().shape[0]
    sum_data = 0
    for i in range(0, count_size):
        new_name = 'see_' + name + '_' + str(i)
        temp = pd.merge(train_data, count[count[name] == i], on=['user_id']).rename(columns={'times': new_name})
        train_have = pd.merge(train_data, temp[['user_id', new_name]], on=['user_id'])
        train_have = train_have[['user_id', new_name]]
        not_have_name = list(set(train_data['user_id'].values) - set(train_have['user_id'].values))
        train_not_have = DF()
        train_not_have['user_id'] = train_data[train_data['user_id'].isin(not_have_name)]['user_id']
        train_not_have['see_' + name + '_' + str(i)] = 0
        temp = pd.concat([train_have, train_not_have], axis=0)
        train_data = pd.merge(train_data, temp, on=['user_id'], how='left')
        sum_data += train_data[new_name].values

    for i in range(0, count_size):
        new_name = 'see_' + name + '_' + str(i)
        train_data[new_name + '_ratio'] = train_data[new_name].values / sum_data

    return train_data


def get_last_window(now):
    if now.min() > 0:
        return 1
    else:
        return 0


def parallelize_df_func(df, func, start, end, num_partitions=21, n_jobs=7):
    df_split = np.array_split(df, num_partitions)
    start_date = [start] * num_partitions
    end_date = [end] * num_partitions
    param_info = zip(df_split, start_date, end_date)
    pool = Pool(n_jobs)
    gc.collect()
    df = pd.concat(pool.map(func, param_info))
    pool.close()
    pool.join()
    gc.collect()
    return df


def get_train(param_info):
    uid = param_info[0]
    start_date = param_info[1]
    end_date = param_info[2]
    t_start = time.time()

    t1 = time.time()

    train_act = check_id(uid, get_transform(action_log, start_date, end_date))
    train_video = check_id(uid, get_transform(video_log, start_date, end_date))
    train_app = check_id(uid, get_transform(app_log, start_date, end_date))
    train_reg = register_log[register_log['user_id'].isin(uid)].rename(columns={'day': 'reg_day'})

    # Get Week
    train_act['week'] = train_act['day'].values % 7
    train_video['week'] = train_video['day'].values % 7
    train_app['week'] = train_app['day'].values % 7

    # Modify Day
    train_reg['reg_day'] = train_reg['reg_day'] - start_date + 1
    train_act['day'] = train_act['day'] - start_date + 1
    train_video['day'] = train_video['day'] - start_date + 1
    train_app['day'] = train_app['day'] - start_date + 1

    end_date = end_date - start_date + 1
    true_start = start_date
    start_date = 1
    t2 = time.time()

    print(start_date, ' To ', end_date, ' Have User: ', len(uid))
    print('Data Prepare Use...', t2 - t1)

    # Build
    train_data = DF()
    train_data['user_id'] = uid  # 1 feature

    print('train_data0.keys():', train_data.keys())
    train_data = get_time_feature('act_', 'day', train_act, train_data, start_date, end_date)
    print('train_data1.keys():', train_data.keys())
    #train_data = get_time_feature('act_', 'day', train_act, train_data, start_date, end_date)
    #print('train_data2.keys():', train_data.keys())
    #train_data = get_time_feature('act_', 'day', train_act, train_data, start_date, end_date)
    #print('train_data3.keys():', train_data.keys())
    print('Act Encoder Finished')
    for i in range(5):
        page_temp = train_act[train_act['page'] == i]
        train_data = get_type_feature('act_page' + str(i) + '_', 'day', page_temp, train_data, start_date, end_date,
                                      end_date - start_date, '_all')
    for i in range(6):
        act_temp = train_act[train_act['action_type'] == i]
        train_data = get_type_feature('act_action' + str(i) + '_', 'day', act_temp, train_data, start_date, end_date,
                                      end_date - start_date, '_all')
    train_data = get_diff_feature('act_', 'diff_day', train_act, train_data, start_date, end_date)
    train_data = get_encoder_feature('act_', 'diff_day', train_act, train_data, start_date, end_date)
    train_data = pd.merge(train_data,
                          train_act.groupby(['user_id']).apply(lambda x: get_mode(x['week'])).reset_index().rename(
                              columns={0: 'act_mode_week' + '_' + str(end_date - start_date)}), on=['user_id'],
                          how='left')

    for i in ['page', 'action_type', 'video_id', 'author_id']:  # 4*3 12 feature
        train_data = get_id_feature('id_act_', i, train_act, train_data, start_date, end_date)
    print(train_data.shape, ' Aci Finished')

    train_data = get_category_count('page', train_act, train_data, start_date, end_date)
    train_data = get_category_count('action_type', train_act, train_data, start_date, end_date)
    print(train_data.shape, ' Category Finished')

    train_data = get_time_feature('video_', 'day', train_video, train_data, start_date, end_date)
    train_data = get_diff_feature('video_', 'diff_day', train_video, train_data, start_date, end_date)
    print(train_data.shape, ' Video Finished')

    train_data = get_time_feature('app_', 'day', train_app, train_data, start_date, end_date)
    train_data = get_diff_feature('app_', 'diff_day', train_app, train_data, start_date, end_date)
    train_data = get_encoder_feature('app_', 'diff_day', train_app, train_data, start_date, end_date)
    t1 = time.time()
    train_data = pd.merge(train_data,
                          train_app.groupby(['user_id']).apply(lambda x: get_mode(x['week'])).reset_index().rename(
                              columns={0: 'app_mode_week' + '_' + str(end_date - start_date)}), on=['user_id'],
                          how='left')
    print(train_data.shape, ' APP Finished')
    train_app['diff2'] = train_app['day'] - train_app.groupby(['user_id'])['day'].shift(2).values
    app_diff = train_app.dropna()
    app_diff = app_diff.groupby(['user_id'], as_index=False).agg({'diff2': ['max', 'min', 'mean', 'std']})
    app_diff.columns = ['user_id', 'app_diff2_max', 'app_diff2_min', 'app_diff2_mean', 'app_diff2_std']
    train_data = pd.merge(train_data, app_diff, on=['user_id'], how='left')
    t2 = time.time()
    print('APP DIFF ', t2 - t1)

    t1 = time.time()
    user_feature = DF(train_data['user_id'].unique())
    user_feature.columns = ['user_id']
    user_feature = user_feature.set_index('user_id')
    user_feature['HowManyPeople_Watch'] = train_act.groupby('author_id').apply(HowManyPeopleWatch)
    user_feature['Most_Handle'] = train_act.groupby('user_id').apply(MostHandle)

    # 计算视频被观看总次数
    video_size = train_act.groupby('video_id').size().reset_index()
    video_size.columns = ['video_id', 'video_watched_times']
    train_act = pd.merge(train_act, video_size, on=['video_id'], how='left')

    # 分别计算每个用户的贡献度和、均、方
    temp = train_act.groupby('user_id').apply(GongXianDu)
    user_feature['GongXianSum'] = temp.apply(lambda x: x[0])
    user_feature['GongXianMean'] = temp.apply(lambda x: x[1])
    user_feature['GongXianStd'] = temp.apply(lambda x: x[2])
    user_feature['GongXianSkeww'] = temp.apply(lambda x: x[3])
    user_feature['GongXianKurtt'] = temp.apply(lambda x: x[4])

    fav_author = train_act.groupby('user_id').apply(FavAuthorCreate)
    user_feature['FavAuthorCreate'] = fav_author.apply(lambda x: x[0])
    user_feature['WatchOtherVideo'] = fav_author.apply(lambda x: x[1])
    train_data = pd.merge(train_data, user_feature.reset_index(), on=['user_id'], how='left')

    t2 = time.time()
    print('Use Time: ', t2 - t1, ' User-Author Finish... ', 'Shape:', train_data.shape)

    train_data = pd.merge(train_data, train_reg[['user_id', 'register_type', 'device_type', 'week', 'reg_day']],
                          on=['user_id'], how='left').rename(columns={'week': 'reg_week'})  # 2
    t_end = time.time()
    print('Get Feature Use All Time: ', t_end - t_start, ' Shape: ', train_data.shape)
    gc.collect()

    return train_data


def data_prepare(read_path=None):
    register_log = pd.read_csv(read_path + 'user_register_log.txt', sep='\t', header=None,
                               dtype={0: np.uint32, 1: np.uint8, 2: np.uint16, 3: np.uint16}).rename(
        columns={0: 'user_id', 1: 'day', 2: 'register_type', 3: 'device_type'})
    action_log = pd.read_csv(read_path + 'user_activity_log.txt', sep='\t', header=None,
                             dtype={0: np.uint32, 1: np.uint8, 2: np.uint8, 3: np.uint32, 4: np.uint32,
                                    5: np.uint8}).rename(
        columns={0: 'user_id', 1: 'day', 2: 'page', 3: 'video_id', 4: 'author_id', 5: 'action_type'})
    app_log = pd.read_csv(read_path + 'app_launch_log.txt', sep='\t', header=None,
                          dtype={0: np.uint32, 1: np.uint8}).rename(columns={0: 'user_id', 1: 'day'})
    video_log = pd.read_csv(read_path + 'video_create_log.txt', sep='\t', header=None,
                            dtype={0: np.uint32, 1: np.uint8}).rename(columns={0: 'user_id', 1: 'day'})

    # Sort By User
    register_log = register_log.sort_values(by=['user_id', 'day'], ascending=True)
    action_log = action_log.sort_values(by=['user_id', 'day'], ascending=True)
    app_log = app_log.sort_values(by=['user_id', 'day'], ascending=True)
    video_log = video_log.sort_values(by=['user_id', 'day'], ascending=True)

    # Diff Day
    t1 = time.time()
    app_log['diff_day'] = app_log.groupby(['user_id'])['day'].diff().fillna(-1).astype(np.int8)
    video_log['diff_day'] = video_log.groupby(['user_id'])['day'].diff().fillna(-1).astype(np.int8)
    action_log['diff_day'] = action_log.groupby(['user_id'])['day'].diff().fillna(-1).astype(np.int8)
    t2 = time.time()
    print('Diff Day Finished... ', t2 - t1)

    # Prepare REGISTER
    register_log['week'] = register_log['day'] % 7
    register_log['rt_dt'] = (register_log['register_type'] + 1) * (register_log['device_type'] + 1)
    register_log['week_rt'] = (register_log['register_type'] + 1) * (register_log['week'] + 1)
    register_log['week_dt'] = (register_log['device_type'] + 1) * (register_log['week'] + 1)
    register_log['use_reg_people'] = register_log.groupby(['register_type'])['user_id'].transform('count').values
    register_log['use_dev_people'] = register_log.groupby(['device_type'])['user_id'].transform('count').values
    register_log['week_rt_use_people'] = register_log.groupby(['week_rt'])['user_id'].transform('count').values
    register_log['week_dt_use_people'] = register_log.groupby(['week_dt'])['user_id'].transform('count').values
    register_log['rt_dt_use_people'] = register_log.groupby(['rt_dt'])['user_id'].transform('count').values

    return register_log, action_log, app_log, video_log


read_path = '../../dataset/log_preprocess/'
register_log, action_log, app_log, video_log = data_prepare(read_path)
train_set = []
for i in range(17, 25):
    train_label = get_label(i, i + 6)
    train_data_part1 = parallelize_df_func(train_label['user_id'], get_train, i - 16, i - 1, 1, 1)
    train_data = pd.merge(train_data_part1,
                          register_log[['user_id', 'use_reg_people', 'week', 'register_type', 'device_type', 'rt_dt',
                                        'week_rt', 'week_dt', 'use_dev_people', 'week_rt_use_people',
                                        'week_dt_use_people',
                                        'rt_dt_use_people']], on=['user_id'], how='left')
    train_data = pd.merge(train_data, train_label, on=['user_id'], how='left')
    train_set.append(train_data)
    del train_data_part1
    gc.collect()

train_data = pd.concat(train_set[0:-1], axis=0).reset_index(drop=True)
valid_data = train_set[-1]
online_data = parallelize_df_func(register_log['user_id'].unique(), get_train, 15, 30, 1, 1)
online_data = pd.merge(online_data,
                       register_log[['user_id', 'use_reg_people', 'week', 'register_type', 'device_type', 'rt_dt',
                                     'week_rt', 'week_dt', 'use_dev_people', 'week_rt_use_people', 'week_dt_use_people',
                                     'rt_dt_use_people']], on=['user_id'], how='left')

write_path = read_path
train_data.to_csv(write_path + 'train_data.csv', index=False)
valid_data.to_csv(write_path + 'valid_data.csv', index=False)
online_data.to_csv(write_path + 'online_data.csv', index=False)
print('Style 1 Feature Engineer Finished...')
