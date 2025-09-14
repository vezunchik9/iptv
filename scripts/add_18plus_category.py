#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для добавления категории 18+ в плейлист
"""

def add_18plus_content():
    """Добавляет категорию 18+ в основной плейлист"""
    
    # Каналы 18+
    adult_content = '''
# === 🔞 18+ (340+ каналов) ===

#EXTINF:-1 tvg-name="Jasmin TV HD" group-title="🔞 18+", Jasmin TV HD
http://109.71.162.112/live/sd.jasminchannel.stream/chunklist_w233748568.m3u8

#EXTINF:-1 tvg-name="Big Ass" group-title="🔞 18+", Big Ass
http://cdn.adultiptv.net/bigass.m3u8

#EXTINF:-1 tvg-name="Big Dick" group-title="🔞 18+", Big Dick
http://cdn.adultiptv.net/bigdick.m3u8

#EXTINF:-1 tvg-name="Blowjob HD" group-title="🔞 18+", Blowjob HD
http://cdn.adultiptv.net/blowjob.m3u8

#EXTINF:-1 tvg-name="Brunette" group-title="🔞 18+", Brunette
http://cdn.adultiptv.net/brunette.m3u8

#EXTINF:-1 tvg-name="Compilation" group-title="🔞 18+", Compilation
http://cdn.adultiptv.net/compilation.m3u8

#EXTINF:-1 tvg-name="Cuckold" group-title="🔞 18+", Cuckold
http://cdn.adultiptv.net/cuckold.m3u8

#EXTINF:-1 tvg-name="Gangbang" group-title="🔞 18+", Gangbang
http://cdn.adultiptv.net/gangbang.m3u8

#EXTINF:-1 tvg-name="Interracial" group-title="🔞 18+", Interracial
http://cdn.adultiptv.net/interracial.m3u8

#EXTINF:-1 tvg-name="Latina" group-title="🔞 18+", Latina
http://cdn.adultiptv.net/latina.m3u8

#EXTINF:-1 tvg-name="Lesbian" group-title="🔞 18+", Lesbian
http://cdn.adultiptv.net/lesbian.m3u8

#EXTINF:-1 tvg-name="Lesbian HD" group-title="🔞 18+", Lesbian HD
http://live.redtraffic.xyz/lesbian.m3u8

#EXTINF:-1 tvg-name="Live Cams" group-title="🔞 18+", Live Cams
http://cdn.adultiptv.net/livecams.m3u8

#EXTINF:-1 tvg-name="Pornstar" group-title="🔞 18+", Pornstar
http://cdn.adultiptv.net/pornstar.m3u8

#EXTINF:-1 tvg-name="POV" group-title="🔞 18+", POV
http://cdn.adultiptv.net/pov.m3u8

#EXTINF:-1 tvg-name="Rough" group-title="🔞 18+", Rough
http://cdn.adultiptv.net/rough.m3u8

#EXTINF:-1 tvg-name="Russian" group-title="🔞 18+", Russian
http://cdn.adultiptv.net/russian.m3u8

#EXTINF:-1 tvg-name="Teen" group-title="🔞 18+", Teen
http://cdn.adultiptv.net/teen.m3u8

#EXTINF:-1 tvg-name="Threesome" group-title="🔞 18+", Threesome
http://cdn.adultiptv.net/threesome.m3u8

#EXTINF:-1 tvg-name="Threesome HD" group-title="🔞 18+", Threesome HD
http://live.redtraffic.xyz/threesome.m3u8

#EXTINF:-1 tvg-name="Jasmin TV" group-title="🔞 18+", Jasmin TV
http://109.71.162.112:1935/live/hd.jasminchannel.stream/chunklist_w359453841.m3u8

#EXTINF:-1 tvg-name="Jasmin TV HD 1" group-title="🔞 18+", Jasmin TV HD 1
http://109.71.162.112:1935/live/hd.jasminchannel.stream/playlist.m3u8

#EXTINF:-1 tvg-name="Shemale Tube TV 2" group-title="🔞 18+", Shemale Tube TV 2
http://www.ast.tv/stream/2/master.m3u8

#EXTINF:-1 tvg-name="RedTraffic Big Ass HD 720" tvg-logo="https://i.ibb.co/mXsbRw6/redtraffic-1.png" group-title="🔞 18+", RedTraffic Big Ass HD 720
http://live.redtraffic.xyz/bigass.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Big Dick HD 720" tvg-logo="https://i.ibb.co/4MZvV06/redtraffic-2.png" group-title="🔞 18+", RedTraffic Big Dick HD 720
http://live.redtraffic.xyz/bigdick.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Big Tits HD 720" tvg-logo="https://i.ibb.co/mFHLXr0/redtraffic-3.png" group-title="🔞 18+", RedTraffic Big Tits HD 720
http://live.redtraffic.xyz/bigtits.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Blowjob HD 720" tvg-logo="https://i.ibb.co/SJW3q6b/redtraffic-4.png" group-title="🔞 18+", RedTraffic Blowjob HD 720
http://live.redtraffic.xyz/blowjob.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Cuckold HD 720" tvg-logo="https://i.ibb.co/tM30GgZ/redtraffic-5.png" group-title="🔞 18+", RedTraffic Cuckold HD 720
http://live.redtraffic.xyz/cuckold.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Fetish HD 720" tvg-logo="https://i.ibb.co/fMBHkf3/redtraffic-6.png" group-title="🔞 18+", RedTraffic Fetish HD 720
http://live.redtraffic.xyz/fetish.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Hardcore HD 720" tvg-logo="https://i.ibb.co/YBhBdmZ/redtraffic-7.png" group-title="🔞 18+", RedTraffic Hardcore HD 720
http://live.redtraffic.xyz/hardcore.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Interracial HD 720" tvg-logo="https://i.ibb.co/cr6JT3y/redtraffic-8.png" group-title="🔞 18+", RedTraffic Interracial HD 720
http://live.redtraffic.xyz/interracial.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Latina HD 720" tvg-logo="https://i.ibb.co/tqvMpfk/redtraffic-9.png" group-title="🔞 18+", RedTraffic Latina HD 720
http://live.redtraffic.xyz/latina.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Lesbian HD 720" tvg-logo="https://i.ibb.co/7NHc8rZ/redtraffic-10.png" group-title="🔞 18+", RedTraffic Lesbian HD 720
http://live.redtraffic.xyz/lesbian.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Milf HD 720" tvg-logo="https://i.ibb.co/g6NV6yP/redtraffic-11.png" group-title="🔞 18+", RedTraffic Milf HD 720
http://live.redtraffic.xyz/milf.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Pornstar HD 720" tvg-logo="https://i.ibb.co/d2YtbXz/redtraffic-12.png" group-title="🔞 18+", RedTraffic Pornstar HD 720
http://live.redtraffic.xyz/pornstar.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic POV HD 720" tvg-logo="https://i.ibb.co/S6HQpRk/redtraffic-13.png" group-title="🔞 18+", RedTraffic POV HD 720
http://live.redtraffic.xyz/pov.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Russian HD 720" tvg-logo="https://i.ibb.co/42pqrPd/redtraffic-14.png" group-title="🔞 18+", RedTraffic Russian HD 720
http://live.redtraffic.xyz/russian.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Teen HD 720" tvg-logo="https://i.ibb.co/6FYJ7Sw/redtraffic-15.png" group-title="🔞 18+", RedTraffic Teen HD 720
http://live.redtraffic.xyz/teen.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="RedTraffic Threesome HD 720" tvg-logo="https://i.ibb.co/R4LT8Yf/redtraffic-16.png" group-title="🔞 18+", RedTraffic Threesome HD 720
http://live.redtraffic.xyz/threesome.m3u8?fluxuslust.m3u8

#EXTINF:-1 tvg-name="Visit-X TV" tvg-logo="https://i.ibb.co/0VZGVJM/visit-x-tv.png" group-title="🔞 18+", Visit-X TV
http://194.116.150.47:1935/vxtv/live_360p/chunklist_w543388767.m3u8

#EXTINF:-1 tvg-name="Visit-X TV HD 720" tvg-logo="https://i.ibb.co/1vv3rLY/visit-x-tv-720.png" group-title="🔞 18+", Visit-X TV HD 720
http://194.116.150.47:1935/vxtv/live_720p/chunklist_w1156491225.m3u8'''

    # Добавляем Brazzers VOD каналы (много каналов VOD)
    brazzers_vod = ""
    for i in range(1, 301):  # 300 каналов Brazzers
        if i == 3 or i == 89 or i == 93 or i == 95 or i == 97 or i == 129 or i == 144 or i == 226:  # пропускаем отсутствующие
            continue
        brazzers_vod += f'''
#EXTINF:-1 tvg-name="Brazzers - VOD {i:03d}" group-title="🔞 18+", Brazzers - VOD {i:03d}
http://static.brazzers.com/scenes/{3350+i}/180sec.flv'''

    # Добавляем Adult 4K VOD
    adult_4k_vod = ""
    adult_4k_urls = [
        "http://videos.galleries.pornpros.com/galleries.tiny4k.com/htdocs/fb01/fb01_chloeamour022714/content/vid01.mp4",
        "http://videos.galleries.pornpros.com/galleries.tiny4k.com/htdocs/fb01/fb01_sabrinabanks071414/content/vid01.mp4",
        "http://videos.galleries.pornpros.com/galleries.tiny4k.com/htdocs/fb01/fb01_tiffanyfox030514/content/vid01.mp4",
        "http://videos.galleries.pornpros.com/galleries.tiny4k.com/htdocs/fb01/fb01_kaceyjordan061914/content/vid01.mp4",
        "http://videos.galleries.pornpros.com/galleries.tiny4k.com/htdocs/fb01/fb01_jennaross040414/content/vid01.mp4",
        "http://videos.galleries.pornpros.com/galleries.tiny4k.com/htdocs/fb01/fb01_kaceyjordan031914/content/vid01.mp4",
        "http://videos.galleries.pornpros.com/galleries.tiny4k.com/htdocs/fb01/fb01_chloefoster021214/content/vid01.mp4",
        "http://videos.galleries.pornpros.com/galleries.tiny4k.com/htdocs/fb01/fb01_dillionharper030614/content/vid01.mp4",
        "http://videos.galleries.pornpros.com/galleries.tiny4k.com/htdocs/fb01/fb01_emmastoned03414/content/vid01.mp4",
        "http://videos.galleries.pornpros.com/galleries.tiny4k.com/htdocs/fb01/fb01_avataylor_emmastoned032514/content/vid01.mp4",
        "http://videos.galleries.pornpros.com/galleries.tiny4k.com/htdocs/fb01/fb01_dakotaskye040314/content/vid01.mp4"
    ]
    
    for i, url in enumerate(adult_4k_urls, 1):
        adult_4k_vod += f'''
#EXTINF:-1 tvg-name="Adult 4K: VOD{i}" tvg-logo="https://bipbap.ru/wp-content/uploads/2018/06/18plus-3.jpg" group-title="🔞 18+", Adult 4K: VOD{i}
{url}'''

    full_content = adult_content + brazzers_vod + adult_4k_vod

    # Читаем текущий плейлист
    try:
        with open('playlists/televizo_main.m3u', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Добавляем 18+ контент в конец плейлиста
        updated_content = content + "\n" + full_content
        
        # Сохраняем обновленный плейлист
        with open('playlists/televizo_main.m3u', 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        print("✅ Категория 🔞 18+ добавлена в основной плейлист")
        
        # Создаем отдельный файл категории 18+
        with open('categories/18+.m3u', 'w', encoding='utf-8') as f:
            f.write('#EXTM3U url-tvg="http://www.teleguide.info/download/new3/jtv.zip"\n')
            f.write('# Категория: 🔞 18+\n')
            f.write('# Каналов: 340+\n')
            f.write('# ВНИМАНИЕ: Контент только для совершеннолетних!\n\n')
            f.write(full_content)
        
        print("✅ Отдельный файл категории 18+ создан")
        
        # Подсчитываем количество добавленных каналов
        new_count = full_content.count('#EXTINF')
        print(f"📊 Добавлено {new_count} каналов 18+")
        
        return new_count
        
    except Exception as e:
        print(f"❌ Ошибка при добавлении 18+ контента: {e}")
        return 0

if __name__ == "__main__":
    print("🔞 Добавление категории 18+ в плейлист")
    print("⚠️ ВНИМАНИЕ: Контент только для совершеннолетних!")
    print("="*50)
    
    count = add_18plus_content()
    if count > 0:
        print(f"\n🎯 Успешно добавлено {count} каналов 18+")
        print("\n⚠️ ПРЕДУПРЕЖДЕНИЯ:")
        print("- Контент предназначен только для совершеннолетних")
        print("- Использование на свой страх и риск")
        print("- Соблюдайте местное законодательство")
        print("- GitHub может ограничить доступ к репозиторию")
    else:
        print("❌ Не удалось добавить категорию 18+")
