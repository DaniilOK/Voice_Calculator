#!/usr/bin/env python
# -*- coding: utf-8 -*-

from sys import byteorder
from array import array
from struct import pack
from subprocess import call

import pyaudio
import wave


THRESHOLD = 800
CHUNK_SIZE = 1024
FORMAT = pyaudio.paInt16
RATE = 16000

text_to_numbers = {'ноль': 0, 'один': 1, 'два': 2, 'три': 3, 'четыре': 4, 'пять': 5, 'шесть': 6, 'семь': 7, 'восемь': 8, 'девять': 9,
               'десять': 10, 'одиннадцать': 11, 'двенадцать': 12, 'тринадцать': 13, 'четырнадцать': 14, 'пятнадцать': 15, 'шестнадцать': 16, 'семнадцать': 17, 'восемнадцать': 18, 'девятнадцать': 19,
               'двадцать': 20, 'тридцать': 30, 'сорок': 40, 'пятьдесят': 50, 'шестьдесят': 60, 'семьдесят': 70, 'восемьдесят': 80, 'девяносто': 90,
               'сто': 100, 'двести': 200, 'триста': 300, 'четыреста': 400, 'пятьсот': 500, 'шестьсот': 600, 'семьсот': 700, 'восемьсот': 800, 'девятьсот': 900}


def is_silent(snd_data):
    """Returns 'True' if below the 'silent' threshold"""
    return max(snd_data) < THRESHOLD


def normalize(snd_data):
    """Average the volume out"""
    MAXIMUM = 16384
    times = float(MAXIMUM)/max(abs(i) for i in snd_data)

    r = array('h')
    for i in snd_data:
        r.append(int(i*times))
    return r


def trim(snd_data):
    """Trim the blank spots at the start and end"""
    def _trim(snd_data):
        snd_started = False
        r = array('h')

        for i in snd_data:
            if not snd_started and abs(i) > THRESHOLD * 5:
                snd_started = True
                r.append(i)
            elif snd_started:
                r.append(i)
        return r

    # Trim to the left
    snd_data = _trim(snd_data)

    # Trim to the right
    snd_data.reverse()
    snd_data = _trim(snd_data)
    snd_data.reverse()
    return snd_data


def add_silence(snd_data, seconds):
    """Add silence to the start and end of 'snd_data' of length 'seconds' (float)"""
    r = array('h', [0 for i in xrange(int(seconds*RATE))])
    r.extend(snd_data)
    r.extend([0 for i in xrange(int(seconds*RATE))])
    return r


def record():
    """
    Record a word or words from the microphone and
    return the data as an array of signed shorts.

    Normalizes the audio, trims silence from the
    start and end, and pads with 0.5 seconds of
    blank sound to make sure VLC et al can play
    it without getting chopped off.
    """
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=1, rate=RATE, input=True, output=True, frames_per_buffer=CHUNK_SIZE)

    num_silent = 0
    snd_started = False

    r = array('h')

    while 1:
        snd_data = array('h', stream.read(CHUNK_SIZE))
        print(snd_data)
        if byteorder == 'big':
            snd_data.byteswap()
        r.extend(snd_data)

        silent = is_silent(snd_data)
        print(silent)

        if silent and snd_started:
            num_silent += 1
        elif not silent and not snd_started:
            snd_started = True

        if snd_started and num_silent > 20:
            break

    sample_width = p.get_sample_size(FORMAT)
    stream.stop_stream()
    stream.close()
    p.terminate()

    r = normalize(r)
    r = trim(r)
    r = add_silence(r, 0.01)
    return sample_width, r


def record_to_file(path):
    """Records from the microphone and outputs the resulting data to 'path'"""
    sample_width, data = record()
    data = pack('<' + ('h'*len(data)), *data)

    wf = wave.open(path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(sample_width)
    wf.setframerate(RATE)
    wf.writeframes(data)
    wf.close()


def split_and_clean(line, begin, delimiters):
    line = line.lstrip(begin).rstrip(";").strip("()")
    splits = line.split("|")
    splits = [split.strip() for split in splits]
    return splits


def get_number_from_words(sentence):
    operations = ['плюс', 'минус', 'умножить', 'разделить']
    pretexts = ['на']

    splits = sentence.split(' ')
    operation = None
    first = 0
    second = 0

    for split in splits:
        if split in pretexts:
            continue

        if split in operations:
            operation = split
            continue

        value = text_to_numbers[split]

        if operation is None:
            first += value
        else:
            second += value

    return {
        'плюс': first + second,
        'минус': first - second,
        'умножить': first * second,
        'разделить': round(first * 1.0 / second,3)
    }[operation]


# def get_sounds_from_number(number):
#     if number == 0:
#         return ['0']
#
#     result = []
#
#     if number < 0:
#         result.append('minus')
#
#     number = abs(number)
#
#     if number == 0:
#         return result.append(0)
#
#     if number // 100 != 0:
#         result.append(str((number // 100) * 100))
#         number = number % 100
#
#     if number > 20:
#         result.append(str((number // 10) * 10))
#         if number % 10 != 0:
#             result.append(str(number % 10))
#     elif number > 0:
#         result.append(str(number))
#
#     return result
#
#
# def play_sounds(playlist):
#     wf = wave.open('sound_numbers/{}.wav'.format(playlist[0]), 'rb')
#
#     p = pyaudio.PyAudio()
#     stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
#                     channels=wf.getnchannels(),
#                     rate=wf.getframerate(),
#                     output=True)
#
#     frames = []
#     for sound in playlist:
#         wf = wave.open('sound_numbers/{}.wav'.format(sound), 'rb')
#
#         data = wf.readframes(CHUNK_SIZE)
#
#         while len(data) > 0:
#             frames.append(data)
#             data = wf.readframes(CHUNK_SIZE)
#
#     for frame in frames:
#         stream.write(frame)
#
#     stream.stop_stream()
#     stream.close()
#     p.terminate()


if __name__ == '__main__':
    out_file = 'result.txt'
    record_file = 'demo.wav'

    open(out_file, 'w').close()
    record_to_file(record_file)

    sentence = call("pocketsphinx_continuous -hmm zero_ru_cont_8k_v3/zero_ru.cd_cont_4000/ -dict calculator.dict -jsgf calculator.jsgf -infile demo.wav 2>/dev/null > result.txt", shell=True)

    sentence = open(out_file, 'r').readline().strip('\n')
    result = get_number_from_words(sentence)

    print(sentence)

    if int(result) != result:
        firstPart = str(result).split('.')[0]
        secondPart = str(result).split('.')[1]
        wordLevel = {
            1: 'десятых',
            2: 'соотых',
            3: 'тысячных'
        }[len(secondPart)]

        call("echo \"" + str(firstPart) + " целых, " + str(secondPart) + " " + wordLevel + "\" | festival --tts --language russian", shell=True)
    else:
        call("echo \"" + str(int(result)) + "\" | festival --tts --language russian", shell=True)

    #call("echo \"" + "12341 целых, 34 соотых" + "\" | festival --tts --language russian", shell=True)
    #playlist = get_sounds_from_number(result)
    #play_sounds(playlist)
