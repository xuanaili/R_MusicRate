// src/config/index.js  全局统一配置文件
// ✅✅✅ 核心维护区【你只需要改这里！】✅✅✅
// 格式：{ tag: '标签名称', minSize: 最小尺寸, maxSize: 最大尺寸, minRate: 最小速率, maxRate: 最大速率, numWeight: 数量权重 }
// 所有专辑标签+呼吸小球动效参数，一站式维护，新增/修改/删除 只操作这个数组即可
const tagBallConfigList = [
  // ===== A 开头 =====
  { tag: 'Abstract HipHop【抽象嘻哈】', minSize: 65, maxSize: 110, minRate: 90, maxRate: 220, numWeight: 2 },
      { tag: 'Acoustic Rock【原声摇滚】', minSize: 65, maxSize: 110, minRate: 90, maxRate: 220, numWeight: 2 },
      { tag: 'Adult Contemporary【成人现代】', minSize: 65, maxSize: 110, minRate: 90, maxRate: 220, numWeight: 2 },
  { tag: 'African Music【非洲音乐】', minSize: 40, maxSize: 80, minRate: 200, maxRate: 400, numWeight: 1 },

  { tag: 'Afrobeats【非洲节奏】', minSize: 50, maxSize: 90, minRate: 160, maxRate: 320, numWeight: 1.3 },

  { tag: 'Afropiano【非洲钢琴】', minSize: 50, maxSize: 90, minRate: 160, maxRate: 320, numWeight: 1.3 },

  { tag: 'Afro Jazz【非洲爵士乐】', minSize: 50, maxSize: 90, minRate: 160, maxRate: 320, numWeight: 1.3 },
   { tag: 'Alt Country【另类乡村】', minSize: 55, maxSize: 95, minRate: 140, maxRate: 280, numWeight: 1.4 },
   { tag: 'Alt Pop【另类流行】', minSize: 55, maxSize: 95, minRate: 140, maxRate: 280, numWeight: 1.4 },
  { tag: 'Alternative Dance【另类舞曲】', minSize: 55, maxSize: 95, minRate: 140, maxRate: 280, numWeight: 1.4 },
  { tag: 'Alternative Metal【另类金属】', minSize: 75, maxSize: 135, minRate: 70, maxRate: 190, numWeight: 2.8 },
  { tag: 'Alternative R&B【另类节奏布鲁斯】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 330, numWeight: 1.2 },
  { tag: 'Alternative Rock【另类摇滚】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2 },
  { tag: 'Ambient【氛围音乐】', minSize: 25, maxSize: 65, minRate: 300, maxRate: 500, numWeight: 0.8 },
  { tag: 'Ambient House【氛围浩室】', minSize: 30, maxSize: 70, minRate: 260, maxRate: 460, numWeight: 0.9 },
  { tag: 'Ambient Techno【氛围科技舞曲】', minSize: 35, maxSize: 75, minRate: 240, maxRate: 440, numWeight: 0.9 },
  { tag: 'Ambient Pop【氛围流行】', minSize: 30, maxSize: 80, minRate: 220, maxRate: 420, numWeight: 1.0 },
      { tag: 'Americana【美国音乐】', minSize: 30, maxSize: 80, minRate: 220, maxRate: 420, numWeight: 1.0 },
  { tag: 'Andalusian Classical Music【安达卢西亚古典音乐】', minSize: 20, maxSize: 60, minRate: 320, maxRate: 520, numWeight: 0.7 },
  { tag: 'Andalusian Folk Music【安达卢西亚民谣】', minSize: 25, maxSize: 65, minRate: 300, maxRate: 500, numWeight: 0.8 },
  { tag: 'Arabic Classical Music【阿拉伯古典音乐】', minSize: 20, maxSize: 55, minRate: 330, maxRate: 530, numWeight: 0.7 },
  { tag: 'Arts and Crafts Rock【工艺美术摇滚】', minSize: 50, maxSize: 100, minRate: 150, maxRate: 300, numWeight: 1.5 },
  { tag: 'Art Pop【艺术流行】', minSize: 45, maxSize: 95, minRate: 160, maxRate: 320, numWeight: 1.3 },
  { tag: 'Art Punk【艺术朋克】', minSize: 60, maxSize: 110, minRate: 110, maxRate: 260, numWeight: 1.8 },
  { tag: 'Art Rock【艺术摇滚】', minSize: 55, maxSize: 115, minRate: 120, maxRate: 270, numWeight: 1.7 },
  { tag: 'Atmospheric Black Metal【氛围黑金属】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  { tag: 'Atmospheric Sludge Metal【氛围泥浆金属】', minSize: 75, maxSize: 135, minRate: 70, maxRate: 190, numWeight: 2.7 },
  { tag: 'Avant Folk【先锋民谣】', minSize: 35, maxSize: 85, minRate: 200, maxRate: 400, numWeight: 1.1 },
  { tag: 'Avant Garde Jazz【先锋派爵士乐】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Avant Garde Metal【先锋派金属】', minSize: 80, maxSize: 140, minRate: 60, maxRate: 180, numWeight: 2.9 },
  { tag: 'Avant Prog【先锋前卫摇滚】', minSize: 65, maxSize: 125, minRate: 90, maxRate: 230, numWeight: 2.1 },
  // ===== B 开头 =====
  { tag: 'Balkan Folk Music【巴尔干民谣】', minSize: 30, maxSize: 70, minRate: 250, maxRate: 450, numWeight: 0.9 },
  { tag: 'Baroque Pop【巴洛克流行】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },
  { tag: 'Batida【巴蒂达】', minSize: 50, maxSize: 100, minRate: 140, maxRate: 290, numWeight: 1.6 },

  { tag: 'Bedroom Pop【卧室流行】', minSize: 85, maxSize: 150, minRate: 50, maxRate: 170, numWeight: 3.2 },
  { tag: 'Beatdown Hardcore【重击硬核】', minSize: 85, maxSize: 150, minRate: 50, maxRate: 170, numWeight: 3.2 },
  { tag: 'Bitpop【芯片流行】', minSize: 40, maxSize: 90, minRate: 190, maxRate: 370, numWeight: 1.2 },
  { tag: 'Black Metal【黑金属】', minSize: 80, maxSize: 145, minRate: 55, maxRate: 175, numWeight: 3.0 },
  { tag: 'Blackgaze【黑凝视】', minSize: 75, maxSize: 135, minRate: 70, maxRate: 190, numWeight: 2.7 },
  { tag: 'Bluegrass【蓝草音乐】', minSize: 30, maxSize: 75, minRate: 230, maxRate: 430, numWeight: 0.9 },
  { tag: 'Blues Rock【蓝调摇滚】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Boogie【布吉乐】', minSize: 50, maxSize: 100, minRate: 150, maxRate: 300, numWeight: 1.5 },
  { tag: 'Boom Bap【砰砰节拍】', minSize: 55, maxSize: 105, minRate: 130, maxRate: 280, numWeight: 1.7 },
  { tag: 'Brazilian Classical Music【巴西古典音乐】', minSize: 25, maxSize: 65, minRate: 310, maxRate: 510, numWeight: 0.8 },
  { tag: 'Brazilian Music【巴西音乐】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Breakcore【碎核】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Britpop【英伦摇滚】', minSize: 50, maxSize: 105, minRate: 130, maxRate: 280, numWeight: 1.7 },
  { tag: 'Brutal Prog【残酷前卫摇滚】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  // ===== C 开头 =====
  { tag: 'Campus Folk【校园民谣】', minSize: 25, maxSize: 70, minRate: 280, maxRate: 480, numWeight: 0.8 },
  { tag: 'Cantopop【粤语流行】', minSize: 40, maxSize: 90, minRate: 200, maxRate: 400, numWeight: 1.1 },
  { tag: 'Chamber Folk【室内民谣】', minSize: 20, maxSize: 60, minRate: 320, maxRate: 520, numWeight: 0.7 },
  { tag: 'Chamber Jazz【室内爵士乐】', minSize: 25, maxSize: 65, minRate: 300, maxRate: 500, numWeight: 0.8 },
  { tag: 'Chamber Music【室内乐】', minSize: 20, maxSize: 55, minRate: 330, maxRate: 530, numWeight: 0.7 },
  { tag: 'Chamber Pop【室内流行】', minSize: 30, maxSize: 80, minRate: 240, maxRate: 440, numWeight: 0.9 },
  { tag: 'Chillwave【冷潮】', minSize: 25, maxSize: 70, minRate: 290, maxRate: 490, numWeight: 0.8 },
  { tag: 'Chillout【弛放音乐】', minSize: 20, maxSize: 60, minRate: 320, maxRate: 520, numWeight: 0.7 },
  { tag: 'Chinese Music【中国音乐】', minSize: 30, maxSize: 75, minRate: 240, maxRate: 440, numWeight: 0.9 },
  { tag: 'Chiptune【芯片音乐】', minSize: 35, maxSize: 80, minRate: 220, maxRate: 420, numWeight: 1.0 },
  { tag: 'Christian Rock【基督教摇滚】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.2 },
  { tag: 'Cinematic Classical【影视古典】', minSize: 35, maxSize: 90, minRate: 200, maxRate: 400, numWeight: 1.1 },
  { tag: 'Classical Crossover【古典跨界】', minSize: 30, maxSize: 80, minRate: 230, maxRate: 430, numWeight: 0.9 },
  { tag: 'Classical Music【古典音乐】', minSize: 20, maxSize: 60, minRate: 330, maxRate: 530, numWeight: 0.7 },
  { tag: 'Classical Period【古典主义时期】', minSize: 20, maxSize: 55, minRate: 340, maxRate: 540, numWeight: 0.7 },

  { tag: 'Cloud Rap【云雾说唱】', minSize: 20, maxSize: 55, minRate: 340, maxRate: 540, numWeight: 0.7 },
  { tag: 'Conscious HipHop【意识嘻哈】', minSize: 50, maxSize: 100, minRate: 150, maxRate: 300, numWeight: 1.5 },
  { tag: 'Contemporary Country【当代乡村】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },
  { tag: 'Contemporary Folk【当代民谣】', minSize: 100, maxSize: 100, minRate: 1500, maxRate: 1500, numWeight: 0.5 },
  { tag: 'Contemporary R&B【当代节奏布鲁斯】', minSize: 45, maxSize: 500, minRate: 400, maxRate: 500, numWeight: 3 },

  { tag: 'Country【乡村音乐】', minSize: 30, maxSize: 80, minRate: 230, maxRate: 430, numWeight: 0.9 },
  { tag: 'Country Blues【乡村蓝调】', minSize: 30, maxSize: 75, minRate: 240, maxRate: 440, numWeight: 0.9 },

  { tag: 'Country Gospel【乡村福音】', minSize: 30, maxSize: 80, minRate: 230, maxRate: 430, numWeight: 0.9 },
  { tag: 'Country Pop【乡村流行】', minSize: 40, maxSize: 90, minRate: 190, maxRate: 380, numWeight: 1.1 },
  { tag: 'Crunk【旷课乐】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },
  { tag: 'Cool Jazz【酷派爵士乐】', minSize: 30, maxSize: 75, minRate: 250, maxRate: 450, numWeight: 0.9 },
  { tag: 'C Pop【华语流行】', minSize: 40, maxSize: 95, minRate: 190, maxRate: 380, numWeight: 1.2 },
  { tag: 'Coldwave【冷潮】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },


  // ===== D 开头 =====
  { tag: 'Dance【舞曲】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Dance Pop【流行舞曲】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },

  { tag: 'Dance Punk【朋克舞曲】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Darkwave【暗潮】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Delta Blues【三角洲蓝调】', minSize: 30, maxSize: 75, minRate: 240, maxRate: 440, numWeight: 0.9 },
  { tag: 'Death Metal【死亡金属】', minSize: 85, maxSize: 150, minRate: 50, maxRate: 160, numWeight: 3.2 },
  { tag: 'Deathgrind【死亡碾核】', minSize: 90, maxSize: 155, minRate: 40, maxRate: 150, numWeight: 3.5 },
  { tag: 'Deep House【深度浩室】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },
  { tag: 'Disco【迪斯科】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Dissonant Black Metal【不协和黑金属】', minSize: 85, maxSize: 150, minRate: 50, maxRate: 160, numWeight: 3.2 },
  { tag: 'Dissonant Death Metal【不协和死亡金属】', minSize: 90, maxSize: 155, minRate: 40, maxRate: 150, numWeight: 3.5 },


  { tag: 'Digicore【数字核】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Doom Metal【厄运金属】', minSize: 80, maxSize: 145, minRate: 55, maxRate: 175, numWeight: 3.0 },
  { tag: 'Drone【嗡鸣音乐】', minSize: 20, maxSize: 60, minRate: 350, maxRate: 550, numWeight: 0.6 },
  { tag: 'Dream Pop【梦幻流行】', minSize: 30, maxSize: 80, minRate: 240, maxRate: 440, numWeight: 0.9 },
  { tag: 'Drum and Bass【鼓打贝斯】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  { tag: 'Drumless【无鼓嘻哈】', minSize: 45, maxSize: 95, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Dungeon Synth【地牢合成器】', minSize: 25, maxSize: 65, minRate: 310, maxRate: 510, numWeight: 0.7 },
  { tag: 'Downtempo【缓拍电子】', minSize: 25, maxSize: 70, minRate: 290, maxRate: 490, numWeight: 0.8 },
  // ===== E 开头 =====
  { tag: 'East Asian Music【东亚音乐】', minSize: 25, maxSize: 70, minRate: 280, maxRate: 480, numWeight: 0.8 },
  { tag: 'East Coast HipHop【东海岸嘻哈】', minSize: 60, maxSize: 110, minRate: 110, maxRate: 260, numWeight: 1.9 },
  { tag: 'EBM【电子身体音乐】', minSize: 65, maxSize: 125, minRate: 90, maxRate: 230, numWeight: 2.1 },
  { tag: 'ECM Style Jazz【ECM 风格爵士乐】', minSize: 25, maxSize: 70, minRate: 300, maxRate: 500, numWeight: 0.8 },
  { tag: 'Egg Punk【鸡蛋朋克】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Electro Disco【电子迪斯科】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
      { tag: 'Electro Industrial【电子工业】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Electronic【电子音乐】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Electronic Dance Music【电子舞曲】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },
  { tag: 'Electropop【电子流行】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },

  { tag: 'Emo【情绪摇滚】', minSize: 60, maxSize: 115, minRate: 110, maxRate: 260, numWeight: 1.9 },
  { tag: 'Emo Pop【情绪流行】', minSize: 50, maxSize: 400, minRate: 150, maxRate: 300, numWeight: 1 },
  { tag: 'Emo Rap【情绪说唱】', minSize: 55, maxSize: 105, minRate: 130, maxRate: 280, numWeight: 1.7 },
  { tag: 'Emo Revival【情绪摇滚复兴】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Emocore【情绪核】', minSize: 60, maxSize: 115, minRate: 110, maxRate: 260, numWeight: 1.9 },
  { tag: 'Epic Collage【史诗拼贴】', minSize: 40, maxSize: 95, minRate: 190, maxRate: 370, numWeight: 1.2 },
  { tag: 'Epic Music【史诗音乐】', minSize: 50, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'English Underground【英国地下音乐】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Easy Listening【轻音乐】', minSize: 20, maxSize: 60, minRate: 330, maxRate: 530, numWeight: 0.7 },


  { tag: 'Experimental【实验音乐】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },
  { tag: 'Experimental Big Band【实验大乐队】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.2 },
  { tag: 'Experimental HipHop【实验嘻哈】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Experimental Rock【实验摇滚】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },
  // ===== F 开头 =====
  { tag: 'Film Score【电影配乐】', minSize: 35, maxSize: 90, minRate: 200, maxRate: 400, numWeight: 1.1 },
  { tag: 'Film Soundtrack【电影原声】', minSize: 30, maxSize: 85, minRate: 220, maxRate: 420, numWeight: 1.0 },

  { tag: 'Folk【民谣音乐】', minSize: 25, maxSize: 70, minRate: 280, maxRate: 480, numWeight: 0.8 },
  { tag: 'Folk Pop【民谣流行】', minSize: 30, maxSize: 80, minRate: 230, maxRate: 430, numWeight: 0.9 },
  { tag: 'Folk Rock【民谣摇滚】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.2 },

  { tag: 'Folktronica【民谣电子】', minSize: 25, maxSize: 70, minRate: 280, maxRate: 480, numWeight: 0.8 },

      { tag: 'Footwork【碎步舞曲】', minSize: 65, maxSize: 125, minRate: 90, maxRate: 230, numWeight: 2.1 },
  { tag: 'Footwork Jungle【碎步丛林舞曲】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },

  { tag: 'Free Improvisation【自由即兴】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },
  { tag: 'Future Bass【未来贝斯】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },

     { tag: 'Funk【放克】', minSize: 50, maxSize: 100, minRate: 150, maxRate: 300, numWeight: 1.5 },
  { tag: 'Funk Brasileiro【巴西放克】', minSize: 50, maxSize: 100, minRate: 150, maxRate: 300, numWeight: 1.5 },
  { tag: 'Funk Rock【放克摇滚】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },

  // ===== G 开头 =====
  { tag: 'Garage Punk【车库朋克】', minSize: 60, maxSize: 115, minRate: 110, maxRate: 260, numWeight: 1.9 },
  { tag: 'Garage Rock Revival【车库摇滚复兴】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Garage Rock【车库摇滚】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Geek Rock【极客摇滚】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Gangsta Rap【匪帮说唱】', minSize: 65, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },
  { tag: 'Glam Rock【华丽摇滚】', minSize: 55, maxSize: 115, minRate: 110, maxRate: 260, numWeight: 1.9 },

  { tag: 'Gospel【福音音乐】', minSize: 75, maxSize: 135, minRate: 70, maxRate: 190, numWeight: 2.7 },
  { tag: 'Gothic Metal【哥特金属】', minSize: 75, maxSize: 135, minRate: 70, maxRate: 190, numWeight: 2.7 },
  { tag: 'Gothic Rock【哥特摇滚】', minSize: 75, maxSize: 135, minRate: 70, maxRate: 190, numWeight: 2.7 },
  { tag: 'Grindcore【碾核】', minSize: 90, maxSize: 155, minRate: 40, maxRate: 150, numWeight: 3.5 },
  { tag: 'Grunge【垃圾摇滚】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },

  { tag: 'Glitch【故障音乐】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Glitch Hop【故障嘻哈】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Glitch Pop【故障流行】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },

  // ===== H 开头 =====
  { tag: 'Hardcore EDM【硬核电子舞曲】', minSize: 75, maxSize: 135, minRate: 70, maxRate: 190, numWeight: 2.7 },
  { tag: 'Hardcore HipHop【硬核嘻哈】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  { tag: 'Hardcore Punk【硬核朋克】', minSize: 80, maxSize: 140, minRate: 60, maxRate: 180, numWeight: 2.9 },
  { tag: 'Hard Rock【硬摇滚】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  { tag: 'Heavy Metal【重金属】', minSize: 85, maxSize: 150, minRate: 50, maxRate: 160, numWeight: 3.2 },
  { tag: 'Heavy Psych【重型迷幻】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },


  { tag: 'HipHop【嘻哈】', minSize: 55, maxSize: 105, minRate: 130, maxRate: 280, numWeight: 1.7 },
  { tag: 'HipHop Soul【嘻哈灵乐】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },

  { tag: 'Hokkien Pop【闽南语流行】', minSize: 40, maxSize: 90, minRate: 200, maxRate: 400, numWeight: 1.1 },
  { tag: 'Honky Tonk【乡村酒吧音乐】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },
  { tag: 'House【浩室音乐】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  // ===== I 开头 =====
  { tag: 'IDM【智能舞曲】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Impressionism【印象主义】', minSize: 25, maxSize: 65, minRate: 310, maxRate: 510, numWeight: 0.8 },
  { tag: 'Indietronica【独立电子】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },
  { tag: 'Indie Folk【独立民谣】', minSize: 30, maxSize: 80, minRate: 230, maxRate: 430, numWeight: 0.9 },
  { tag: 'Indie Pop【独立流行】', minSize: 40, maxSize: 90, minRate: 190, maxRate: 380, numWeight: 1.1 },
  { tag: 'Indie Rock【独立摇滚】', minSize: 50, maxSize: 105, minRate: 130, maxRate: 280, numWeight: 1.7 },
  { tag: 'Industrial Hardcore【工业硬核】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  { tag: 'Industrial HipHop【工业嘻哈】', minSize: 65, maxSize: 125, minRate: 90, maxRate: 230, numWeight: 2.1 },
  { tag: 'Industrial Metal【工业金属】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  { tag: 'Industrial Noise【工业噪音】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  { tag: 'Industrial Rock【工业摇滚】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  { tag: 'Instrumental HipHop【器乐嘻哈】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  // ===== J 开头 =====
  { tag: 'Jangle Pop【叮砰流行】', minSize: 40, maxSize: 90, minRate: 190, maxRate: 380, numWeight: 1.1 },

      { tag: 'Jazz【爵士乐】', minSize: 30, maxSize: 80, minRate: 230, maxRate: 430, numWeight: 0.9 },
  { tag: 'Jazz Funk【爵士放克】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
      { tag: 'Jazz Fusion【爵士融合】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
      { tag: 'Jazz Pop【爵士流行】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  { tag: 'Jazz Rap【爵士说唱】', minSize: 50, maxSize: 100, minRate: 150, maxRate: 300, numWeight: 1.5 },
  { tag: 'Jazz Rock【爵士摇滚】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },

  { tag: 'J Pop【日本流行】', minSize: 40, maxSize: 95, minRate: 190, maxRate: 380, numWeight: 1.2 },
  { tag: 'J Rock【日本摇滚】', minSize: 65, maxSize: 110, minRate: 90, maxRate: 220, numWeight: 2 },
  { tag: 'Jerk【杰尔克舞曲】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  // ===== K 开头 =====
  { tag: 'Kawaii Future Bass【可爱未来贝斯】', minSize: 40, maxSize: 90, minRate: 190, maxRate: 380, numWeight: 1.1 },

  { tag: 'K Pop【韩国流行】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Kuduro【库杜罗】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  // ===== L 开头 =====
  { tag: 'Ladino Folksong【拉迪诺民谣】', minSize: 25, maxSize: 65, minRate: 300, maxRate: 500, numWeight: 0.8 },
  { tag: 'Latin Pop【拉丁流行】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  // ===== M 开头 =====
  { tag: 'Maghrebi Music【马格里布音乐】', minSize: 30, maxSize: 75, minRate: 240, maxRate: 440, numWeight: 0.9 },
  { tag: 'Maqāmic Music【玛卡姆音乐】', minSize: 25, maxSize: 65, minRate: 310, maxRate: 510, numWeight: 0.8 },
  { tag: 'Mandopop【华语流行】', minSize: 40, maxSize: 90, minRate: 200, maxRate: 400, numWeight: 1.1 },
  { tag: 'Math Rock【数学摇滚】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },
  { tag: 'Melodic Death Metal【旋律死亡金属】', minSize: 80, maxSize: 140, minRate: 60, maxRate: 180,  numWeight: 2.9 },
  { tag: 'Melodic Hardcore【旋律硬核】', minSize: 80, maxSize: 140, minRate: 60, maxRate: 180,  numWeight: 2.9 },
  { tag: 'Microhouse【微型浩室】', minSize: 30, maxSize: 75, minRate: 240, maxRate: 440, numWeight: 0.9 },
  { tag: 'Modern Classical【现代古典】', minSize: 25, maxSize: 70, minRate: 290, maxRate: 490, numWeight: 0.8 },
  { tag: 'Modal Jazz【调式爵士乐】', minSize: 30, maxSize: 80, minRate: 230, maxRate: 430, numWeight: 0.9 },
  { tag: 'MPB【巴西流行音乐】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Mexican Folk Music【墨西哥民谣】', minSize: 30, maxSize: 75, minRate: 240, maxRate: 440, numWeight: 0.9 },
  { tag: 'Mexican Music Hispanic【西班牙裔墨西哥音乐】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },
  // ===== N 开头 =====
  { tag: 'Neo Medieval Folk【新中世纪民谣】', minSize: 25, maxSize: 65, minRate: 300, maxRate: 500, numWeight: 0.8 },
  { tag: 'Neo Psychedelia【新迷幻】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Neo Prog【新前卫摇滚】', minSize: 65, maxSize: 125, minRate: 90, maxRate: 230, numWeight: 2.1 },
  { tag: 'Neo Soul【新灵魂乐】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  { tag: 'New Age【新世纪音乐】', minSize: 20, maxSize: 60, minRate: 330, maxRate: 530, numWeight: 0.7 },
  { tag: 'New Rave【新锐舞】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },
  { tag: 'New Wave【新浪潮】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Nordic Folk Music【北欧民谣】', minSize: 25, maxSize: 65, minRate: 300, maxRate: 500, numWeight: 0.8 },
  { tag: 'Nordic Music【北欧音乐】', minSize: 25, maxSize: 70, minRate: 280, maxRate: 480, numWeight: 0.8 },
  { tag: 'Noise Pop【噪音流行】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Noise Rock【噪音摇滚】', minSize: 65, maxSize: 125, minRate: 90, maxRate: 230, numWeight: 2.1 },
  { tag: 'Nu Disco【新迪斯科】', minSize: 50, maxSize: 400, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Nu Jazz【新爵士】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  // ===== P 开头 =====
  { tag: 'Parody Music【恶搞音乐】', minSize: 40, maxSize: 90, minRate: 190, maxRate: 380, numWeight: 1.1 },
  { tag: 'Piano Rock【钢琴摇滚】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },

  { tag: 'Plugg【Plugg】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },
  { tag: 'Plunderphonics【掠夺音效】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },

  { tag: 'Pop【流行音乐】', minSize: 40, maxSize: 90, minRate: 200, maxRate: 400, numWeight: 1.1 },
  { tag: 'Pop Punk【流行朋克】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  { tag: 'Pop Rap【流行说唱】', minSize: 50, maxSize: 100, minRate: 150, maxRate: 300, numWeight: 1.5 },
  { tag: 'Pop Rock【流行摇滚】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Pop Soul【流行灵魂乐】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },

  { tag: 'Post Hardcore【后硬核】', minSize: 80, maxSize: 150, minRate: 50, maxRate: 180, numWeight: 3 },
  { tag: 'Post Industrial【后工业音乐】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  { tag: 'Post Metal【后金属】', minSize: 75, maxSize: 135, minRate: 70, maxRate: 190, numWeight: 2.7 },
  { tag: 'Post Punk Revival【后朋克复兴】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },
  { tag: 'Post Punk【后朋克】', minSize: 60, maxSize: 115, minRate: 110, maxRate: 260, numWeight: 1.9 },
  { tag: 'Post Rock【后摇滚】', minSize: 50, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Power Metal【力量金属】', minSize: 80, maxSize: 145, minRate: 55, maxRate: 175, numWeight: 3.0 },
  { tag: 'Power Pop【强力流行】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Progressive Bluegrass【前卫蓝草】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Progressive Country【前卫乡村】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Progressive Electronic【前卫电子】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  { tag: 'Progressive Metal【前卫金属】', minSize: 75, maxSize: 135, minRate: 70, maxRate: 190, numWeight: 2.7 },
  { tag: 'Progressive Pop【前卫流行】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  { tag: 'Progressive Rock【前卫摇滚】', minSize: 65, maxSize: 125, minRate: 90, maxRate: 230, numWeight: 2.1 },
  { tag: 'Progressive Soul【前卫灵魂乐】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },

  { tag: 'Psychedelia【迷幻音乐】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Psychedelic Folk【迷幻民谣】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Psychedelic Pop【迷幻流行】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  { tag: 'Psychedelic Rock【迷幻摇滚】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },
  { tag: 'Psychedelic Soul【迷幻灵魂乐】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },

  { tag: 'Punk【朋克音乐】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  { tag: 'Punk Rock【朋克摇滚】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },

  { tag: 'Political HipHop【政治嘻哈】', minSize: 55, maxSize: 105, minRate: 130, maxRate: 280, numWeight: 1.7 },
  // ===== R 开头 =====
  { tag: 'Rage【暴怒说唱】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  { tag: 'Rap Metal【说唱金属】', minSize: 75, maxSize: 135, minRate: 70, maxRate: 190, numWeight: 2.7 },
  { tag: 'Rap Rock【说唱摇滚】', minSize: 65, maxSize: 125, minRate: 90, maxRate: 230, numWeight: 2.1 },
      { tag: 'Reggae【雷鬼】', minSize: 65, maxSize: 125, minRate: 90, maxRate: 230, numWeight: 2.1 },
  { tag: 'Rhythm & Blues【节奏布鲁斯】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },

  { tag: 'Rock【摇滚音乐】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },
  { tag: 'Rock Opera【摇滚歌剧】', minSize: 50, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Rock and Roll【摇滚乐】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Rockabilly【山地摇滚】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },

  { tag: 'R&B【节奏布鲁斯】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  // ===== S 开头 =====
  { tag: 'Samba【桑巴】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  { tag: 'Screamo【尖叫情绪】', minSize: 80, maxSize: 140, minRate: 60, maxRate: 180, numWeight: 2.9 },
  { tag: 'Scenes Movements【场景运动】', minSize: 40, maxSize: 90, minRate: 190, maxRate: 380, numWeight: 1.1 },
  { tag: 'Afrofuturism【非洲未来主义】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Clube da esquina【街角俱乐部】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Windmill Scene【风车场景】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Seapunk【海洋朋克】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  { tag: 'Sephardic Music【塞法迪音乐】', minSize: 25, maxSize: 65, minRate: 300, maxRate: 500, numWeight: 0.8 },
  { tag: 'Shimokita Kei【下北系】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Shoegaze【盯鞋摇滚】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
      { tag: 'Singer Songwriter【创作歌手】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Slacker Rock【懒汉摇滚】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  { tag: 'Sludge Metal【泥浆金属】', minSize: 80, maxSize: 145, minRate: 55, maxRate: 175, numWeight: 3.0 },
  { tag: 'Slowcore【慢核】', minSize: 30, maxSize: 80, minRate: 230, maxRate: 430, numWeight: 0.9 },
  { tag: 'Smooth Soul【平滑灵魂乐】', minSize: 40, maxSize: 90, minRate: 190, maxRate: 380, numWeight: 1.1 },
  { tag: 'Soft Rock【软摇滚】', minSize: 40, maxSize: 90, minRate: 190, maxRate: 380, numWeight: 1.1 },
  { tag: 'Sound Collage【声音拼贴】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },
  { tag: 'Soundtrack【原声音乐】', minSize: 35, maxSize: 90, minRate: 200, maxRate: 400, numWeight: 1.1 },
  { tag: 'Southern HipHop【南部嘻哈】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },
  { tag: 'Space Ambient【太空氛围】', minSize: 20, maxSize: 60, minRate: 330, maxRate: 530, numWeight: 0.7 },
  { tag: 'Space Disco【太空迪斯科】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Space Rock【太空摇滚】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },
  { tag: 'Ska Punk【斯卡朋克】', minSize: 60, maxSize: 115, minRate: 110, maxRate: 260, numWeight: 1.9 },
  { tag: 'Sophisti Pop【精致流行】', minSize: 40, maxSize: 90, minRate: 190, maxRate: 380, numWeight: 1.1 },

  { tag: 'Soul【灵魂乐】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  { tag: 'Soul Jazz【灵魂爵士乐】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },

  { tag: 'Spiritual Jazz【灵性爵士乐】', minSize: 30, maxSize: 80, minRate: 230, maxRate: 430, numWeight: 0.9 },
  { tag: 'Standards【标准曲】', minSize: 30, maxSize: 80, minRate: 230, maxRate: 430, numWeight: 0.9 },
  { tag: 'Stoner Rock【石人摇滚】', minSize: 70, maxSize: 130, minRate: 80, maxRate: 200, numWeight: 2.5 },
  { tag: 'Stomp and Holler【跺脚吟唱民谣】', minSize: 30, maxSize: 80, minRate: 230, maxRate: 430, numWeight: 0.9 },
  { tag: 'Street Punk【街头朋克】', minSize: 30, maxSize: 80, minRate: 230, maxRate: 430, numWeight: 0.9 },
  { tag: 'Sunshine Pop【阳光流行】', minSize: 40, maxSize: 90, minRate: 190, maxRate: 380, numWeight: 1.1 },
  { tag: 'Surf Music【冲浪音乐】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  { tag: 'Swing【摇摆乐】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Synth Funk【合成器放克】', minSize: 50, maxSize: 100, minRate: 150, maxRate: 300, numWeight: 1.5 },
  { tag: 'Synthpop【合成器流行】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  { tag: 'Symphonic Metal【交响金属】', minSize: 75, maxSize: 135, minRate: 70, maxRate: 190, numWeight: 2.7 },
  { tag: 'Symphonic Prog【交响前卫摇滚】', minSize: 65, maxSize: 125, minRate: 90, maxRate: 230, numWeight: 2.1 },
  { tag: 'Symphonic Rock【交响摇滚】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },
  // ===== T 开头 =====
  { tag: 'Tech House【科技浩室】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Technical Death Metal【技术死亡金属】', minSize: 90, maxSize: 155, minRate: 40, maxRate: 150, numWeight: 3.5 },
  { tag: 'Techno【科技舞曲】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'Television Music【电视配乐】', minSize: 35, maxSize: 90, minRate: 200, maxRate: 400, numWeight: 1.1 },
  { tag: 'Third Wave Ska【第三波斯卡】', minSize: 55, maxSize: 110, minRate: 120, maxRate: 270, numWeight: 1.8 },
  { tag: 'Tropicália【热带主义】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  { tag: 'Trap【陷阱说唱】', minSize: 65, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },

  { tag: 'Trap EDM【陷阱电子舞曲】', minSize: 65, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },

  { tag: 'Traditional Country【传统乡村】', minSize: 25, maxSize: 70, minRate: 280, maxRate: 480, numWeight: 0.8 },
  { tag: 'Traditional Folk Music【传统民谣】', minSize: 25, maxSize: 70, minRate: 280, maxRate: 480, numWeight: 0.8 },
  { tag: 'Traditional Pop【传统流行】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },
  { tag: 'Tradi Moderne Congolais【刚果传统现代乐】', minSize: 40, maxSize: 90, minRate: 180, maxRate: 360, numWeight: 1.2 },
  { tag: 'Trip Hop【神游舞曲】', minSize: 30, maxSize: 80, minRate: 240, maxRate: 440, numWeight: 0.9 },
  { tag: 'Turkish Classical Music【土耳其古典音乐】', minSize: 25, maxSize: 65, minRate: 300, maxRate: 500, numWeight: 0.8 },
      { tag: 'Turkish Folk Music【土耳其民谣】', minSize: 25, maxSize: 65, minRate: 300, maxRate: 500, numWeight: 0.8 },
  { tag: 'Turkish Music【土耳其音乐】', minSize: 30, maxSize: 75, minRate: 240, maxRate: 440, numWeight: 0.9 },
  // ===== U 开头 =====
  { tag: 'UK Bass【英国贝斯乐】', minSize: 60, maxSize: 120, minRate: 100, maxRate: 250, numWeight: 2.0 },
  { tag: 'UK Garage【英国车库】', minSize: 50, maxSize: 105, minRate: 140, maxRate: 290, numWeight: 1.6 },
  { tag: 'UK HipHop【英国嘻哈】', minSize: 60, maxSize: 110, minRate: 110, maxRate: 260, numWeight: 1.9 },
  // ===== V 开头 =====
  { tag: 'Vapor【蒸汽音乐】', minSize: 25, maxSize: 70, minRate: 290, maxRate: 490, numWeight: 0.8 },
  { tag: 'Vaporwave【蒸汽波】', minSize: 25, maxSize: 70, minRate: 290, maxRate: 490, numWeight: 0.8 },
  { tag: 'V Pop【越南流行】', minSize: 40, maxSize: 90, minRate: 200, maxRate: 400, numWeight: 1.1 },
  { tag: 'Vocal Jazz【人声爵士乐】', minSize: 35, maxSize: 85, minRate: 210, maxRate: 410, numWeight: 1.0 },
  { tag: 'Vocal Surf【人声冲浪乐】', minSize: 45, maxSize: 95, minRate: 170, maxRate: 340, numWeight: 1.3 },
  // ===== W 开头 =====
  { tag: 'West Coast HipHop【西海岸嘻哈】', minSize: 60, maxSize: 110, minRate: 110, maxRate: 260, numWeight: 1.9 },
  { tag: 'Western Classical Music【西方古典音乐】', minSize: 20, maxSize: 60, minRate: 330, maxRate: 530, numWeight: 0.7 },
  // ===== Z 开头 =====
  { tag: 'Zhongguo feng【中国风】', minSize: 30, maxSize: 70, minRate: 250, maxRate: 450, numWeight: 0.9 }
];

// ✅ 小球动效默认兜底配置 (无匹配标签时使用)
const defaultBallConfig = { minSize: 40, maxSize: 80, minRate: 200, maxRate: 400, numWeight: 1 };

// ✅ 自动生成：专辑纯标签数组 (albumTagOptions) - 完全和你原格式一致
const albumTagOptions = tagBallConfigList.map(item => item.tag);

// ✅ 自动生成：标签-小球参数映射对象 (ballConfig) - 完全和你原格式一致
const ballConfig = tagBallConfigList.reduce((config, item) => {
  const { tag, ...ballParams } = item;
  config[tag] = ballParams;
  return config;
}, { default: defaultBallConfig });

// ✅ 最终导出，组件调用方式 完全不变！
export default {
  albumTagOptions,
  ballConfig
};