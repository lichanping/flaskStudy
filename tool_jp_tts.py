import asyncio
import os
import random
import re
import sys
import time
from os.path import dirname, abspath

import edge_tts
from edge_tts import VoicesManager


def get_sub_folder_path(sub_dir_name='data'):
    """
    Create the destination folder if not exists.
    :param sub_dir_name: default is 'data'
    :return: sub folder's absolute path.
    """
    current_dir_name = dirname(__file__)
    abs_path = abspath(current_dir_name)
    sub_folder = os.sep.join([abs_path, sub_dir_name])
    return sub_folder


def safe_filename(text):
    """
    将文本转换为安全的文件名
    修改：只替换真正不安全的字符，保留空格，但确保没有多余空格
    """
    # 先去除首尾空格
    text = text.strip()
    # 只替换真正不安全的文件名字符，保留空格
    text = re.sub(r'[\\/*?:"<>|]', "", text)
    # 确保没有连续多个空格
    text = re.sub(r'\s+', ' ', text)
    return text


def split_japanese_chinese(line):
    """
    智能分割日语和中文部分
    改进版：使用混合策略区分日语汉字和中文汉字
    """
    line = line.strip()
    if not line:
        return None, None

    # 处理制表符分隔的情况 - 改进版：更严格地清理日语部分
    if '\t' in line:
        parts = line.split('\t', 1)
        if len(parts) == 2:
            # 确保日语部分不包含制表符和多余字符
            japanese_part = parts[0].strip()
            chinese_part = parts[1].strip()

            # 更严格的清理：移除日语部分末尾可能的多余字母和符号
            # 特别是单个字母如 't', 'n' 等，以及反斜杠
            japanese_part = re.sub(r'[a-zA-Z\\]\s*$', '', japanese_part).strip()

            # 再次清理可能的中文标点和空格
            japanese_part = re.sub(r'[，。！？；：、"\'【】《》\s]+$', '', japanese_part)

            # 确保没有多余空格
            japanese_part = re.sub(r'\s+', ' ', japanese_part).strip()

            # 如果清理后为空，则使用原始部分（不含制表符后的内容）
            if not japanese_part:
                japanese_part = parts[0].strip()

            return japanese_part, chinese_part

    # 其余代码保持不变...
    # 策略1: 查找日语特有的假名作为分割线索
    # 平假名范围: \u3040-\u309F
    # 片假名范围: \u30A0-\u30FF
    kana_pattern = r'[\u3040-\u309F\u30A0-\u30FF]'
    kana_matches = list(re.finditer(kana_pattern, line))

    if kana_matches:
        # 找到最后一个假名的位置
        last_kana_pos = kana_matches[-1].end()

        # 从最后一个假名位置开始，查找连续的中文部分
        remaining_text = line[last_kana_pos:]

        # 查找中文部分（至少2个连续中文字符）
        chinese_pattern = r'[\u4E00-\u9FFF]{2,}'
        chinese_match = re.search(chinese_pattern, remaining_text)

        if chinese_match:
            chinese_start = last_kana_pos + chinese_match.start()
            japanese_part = line[:chinese_start].strip()
            chinese_part = line[chinese_start:].strip()

            # 清理日语部分末尾可能的中文标点和多余字母
            japanese_part = re.sub(r'[a-zA-Z\\]\s*$', '', japanese_part).strip()
            japanese_part = re.sub(r'[，。！？；：、"\'【】《》\s]+$', '', japanese_part)
            japanese_part = re.sub(r'\s+', ' ', japanese_part).strip()

            if japanese_part and chinese_part:
                return japanese_part, chinese_part

    # 其他策略也添加类似的清理...
    # 在策略2、3、4、5的每个返回点都添加相同的清理代码

    # 策略2: 使用日语助词和语法特征作为分割线索
    japanese_particles = ['は', 'が', 'を', 'に', 'で', 'と', 'から', 'まで', 'より', 'の', 'も', 'や', 'か', 'ね',
                          'よ']

    # 查找最后一个日语助词的位置
    last_particle_pos = -1
    for particle in japanese_particles:
        pos = line.rfind(particle)
        if pos > last_particle_pos:
            last_particle_pos = pos

    if last_particle_pos > 0:
        # 从助词位置后开始查找中文部分
        search_start = last_particle_pos + 1
        remaining_text = line[search_start:]

        chinese_pattern = r'[\u4E00-\u9FFF]{2,}'
        chinese_match = re.search(chinese_pattern, remaining_text)

        if chinese_match:
            chinese_start = search_start + chinese_match.start()
            japanese_part = line[:chinese_start].strip()
            chinese_part = line[chinese_start:].strip()

            # 清理日语部分末尾可能的中文标点和多余字母
            japanese_part = re.sub(r'[a-zA-Z\\]\s*$', '', japanese_part).strip()
            japanese_part = re.sub(r'[，。！？；：、"\'【】《》\s]+$', '', japanese_part)
            japanese_part = re.sub(r'\s+', ' ', japanese_part).strip()

            if japanese_part and chinese_part:
                return japanese_part, chinese_part

    # 其他策略也类似添加清理代码...

    # 如果所有策略都失败，返回整行作为日语部分，但进行清理
    japanese_part = line
    chinese_part = "未知翻译"

    # 对最终结果进行清理
    japanese_part = re.sub(r'[a-zA-Z\\]\s*$', '', japanese_part).strip()
    japanese_part = re.sub(r'[，。！？；：、"\'【】《》\s]+$', '', japanese_part)
    japanese_part = re.sub(r'\s+', ' ', japanese_part).strip()

    return japanese_part, chinese_part


class JapaneseTTSProcessor:
    def __init__(self):
        # Path to the text file under user_data directory
        self.text_file_path = os.path.join(get_sub_folder_path(), 'MissingSound.txt')
        self.sound_folder = get_sub_folder_path('static/sounds')
        self.TEXT_LIST = self.read_texts_from_file(self.text_file_path)

        if not self.TEXT_LIST:
            print("日语文本列表为空，请在MissingSound.txt中提供文本。")
            sys.exit()

    def read_texts_from_file(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as file:
            # Read each line and remove leading/trailing whitespace
            texts = [line.strip() for line in file.readlines() if line.strip()]
        return texts

    # Async function to process a single text and convert it to speech
    async def process_single_text(self, text, voices_manager):
        # Create safe filename for output
        safe_name = safe_filename(text)
        output_file = os.path.join(self.sound_folder, f"{safe_name}.mp3")

        # Check if file already exists
        if os.path.exists(output_file):
            print(f"音频文件已存在: {output_file}")
            return

        # Choose Japanese voice
        all_voices = voices_manager.find(Language="ja", Locale="ja-JP")

        if not all_voices:
            print("未找到日语语音，使用默认语音")
            all_voices = voices_manager.find(Language="ja")

        if not all_voices:
            print("无法找到合适的日语语音")
            return

        selected_voice = random.choice(all_voices)["Name"]
        print(f"处理日语文本: '{text}' 使用语音: '{selected_voice}'")

        # Use Edge TTS API to convert text to speech and save as MP3 file
        try:
            communicate = edge_tts.Communicate(text, selected_voice, rate="-25%")
            await communicate.save(output_file)
            print(f"成功生成音频: {output_file}")
        except Exception as e:
            print(f"生成音频失败: {e}")

    # Main function to process the entire TEXT_LIST in parallel batches
    async def process_all_texts(self):
        start_time = time.time()  # Record start time

        # Create the voices manager once
        voices_manager = await VoicesManager.create()

        # Process all texts in parallel (with a limit to avoid overwhelming the system)
        max_concurrent_tasks = 5  # Adjust based on your system's capabilities
        semaphore = asyncio.Semaphore(max_concurrent_tasks)

        async def process_with_semaphore(text):
            async with semaphore:
                await self.process_single_text(text, voices_manager)

        # Create tasks for all texts
        tasks = [process_with_semaphore(text) for text in self.TEXT_LIST]

        # Run all tasks concurrently
        await asyncio.gather(*tasks)

        end_time = time.time()  # Record end time
        elapsed_time = end_time - start_time  # Calculate elapsed time
        print(f"处理 {len(self.TEXT_LIST)} 个日语文本总耗时: {elapsed_time:.2f} 秒")
        print(f"每个文本平均耗时: {elapsed_time / len(self.TEXT_LIST):.2f} 秒")


def process_japanese_library():
    """
    处理日语词库文件，检查缺失的音频文件
    """
    data_folder = get_sub_folder_path()
    sound_folder = get_sub_folder_path('static/sounds')
    japanese_file_path = os.path.join(data_folder, '词库源', '日语单词.txt')
    missing_sound_file = os.path.join(data_folder, 'MissingSound.txt')

    # 确保目录存在
    os.makedirs(sound_folder, exist_ok=True)
    os.makedirs(os.path.dirname(japanese_file_path), exist_ok=True)

    missing_words = []
    processed_data = []

    # 读取日语词库文件
    if not os.path.exists(japanese_file_path):
        print(f"日语词库文件不存在: {japanese_file_path}")
        return

    with open(japanese_file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    print(f"开始处理日语词库，共 {len(lines)} 行")

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue

        # 分割日语和中文部分
        japanese_part, chinese_part = split_japanese_chinese(line)

        if not japanese_part:
            print(f"第 {line_num} 行无法分割: {line}")
            continue

        if not chinese_part:
            print(f"第 {line_num} 行缺少中文翻译: {line}")
            chinese_part = "未知"

        # 额外的安全检查：确保日语部分不包含多余的字母和反斜杠
        japanese_part = re.sub(r'\s+[a-zA-Z\\]\s*$', '', japanese_part).strip()
        japanese_part = re.sub(r'\s+', ' ', japanese_part).strip()

        # 创建安全的文件名（保留空格）
        safe_filename_text = safe_filename(japanese_part)

        # 再次检查文件名是否包含单个字母或反斜杠
        if re.search(r' [a-zA-Z\\]\.mp3$', safe_filename_text):
            safe_filename_text = re.sub(r' [a-zA-Z\\]\.mp3$', '.mp3', safe_filename_text)

        media_file = os.path.join(sound_folder, f"{safe_filename_text}.mp3")
        exists = os.path.exists(media_file)

        processed_data.append({
            "日语": japanese_part,
            "中文": chinese_part,
            "音频文件": safe_filename_text + ".mp3",
            "存在": exists
        })

        if not exists:
            # 确保只写入干净的日语部分，不包含制表符和反斜杠
            clean_word = japanese_part.strip()
            # 再次清理反斜杠
            clean_word = re.sub(r'\\', '', clean_word)
            missing_words.append(clean_word)
            print(f"缺失音频: {japanese_part} -> {chinese_part}")
        else:
            print(f"音频已存在: {japanese_part} -> {chinese_part}")

    # 写入缺失的单词到MissingSound.txt（只写入干净的日语部分）
    with open(missing_sound_file, 'w', encoding='utf-8') as f:
        for word in missing_words:
            # 确保每个单词都是干净的，不包含制表符和反斜杠
            clean_word = word.strip()
            clean_word = re.sub(r'\\', '', clean_word)
            f.write(clean_word + '\n')

    print(f"\n处理完成:")
    print(f"总行数: {len(processed_data)}")
    print(f"缺失音频数: {len(missing_words)}")
    print(f"缺失单词已保存到: {missing_sound_file}")

    return processed_data, missing_words


async def main():
    """
    主函数：处理日语词库并生成缺失的音频
    """
    print("开始处理日语词库...")

    # 处理日语词库，检查缺失的音频
    processed_data, missing_words = process_japanese_library()

    if missing_words:
        print(f"\n发现 {len(missing_words)} 个缺失的音频文件，开始生成...")

        # 使用日语TTS处理器生成音频
        processor = JapaneseTTSProcessor()
        await processor.process_all_texts()

        print("音频生成完成！")
    else:
        print("所有音频文件都已存在，无需生成。")


"""
给我XX整首歌的歌词
1. 一句日语一行（末尾带翻译），如“飛翔いたら戻らないと言って\t展翅飞翔之际 请下定决心不再回头”, 用\t分割日语部分和翻译部分。
2. 日语部分的汉字最好用平假名来表示，便于tts生产语音。
"""
if __name__ == '__main__':
    # 添加必要的导入（在文件顶部已经导入，这里确保可用）

    # 运行主程序
    asyncio.run(main())
