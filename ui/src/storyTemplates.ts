import type { StoryProject } from "./api";

export type StoryTemplateId = "blank" | "gothic-fantasy";

export type StoryTemplateDefinition = {
  id: StoryTemplateId;
  label: string;
  name: string;
  genre: string;
  summary: string;
  description: string;
  contents: string[];
};

type IdFactory = (prefix: string) => string;
type ProjectOverrides = Partial<Pick<StoryProject, "name" | "genre" | "summary">>;

export const storyTemplates: StoryTemplateDefinition[] = [
  {
    id: "blank",
    label: "空白故事",
    name: "我的故事",
    genre: "未分类",
    summary: "",
    description: "只创建第一章，从自己的想法开始。",
    contents: ["1 章", "无预设角色", "无预设世界"],
  },
  {
    id: "gothic-fantasy",
    label: "奇幻演示",
    name: "灰烬月冠",
    genre: "哥特奇幻",
    summary:
      "猎夜骑士罗文在押送夜裔继承人伊蕾娅的雨夜，被一份古老月契绑定。教廷要用她开启封印，夜裔议会要她继承空王座；两个彼此敌视的人必须共同查清十二年前的焚城真相。",
    description: "原创哥特奇幻起点，围绕骑士誓言、夜裔王权、身份谜团与敌对共生展开。",
    contents: ["3 章正文", "5 名角色", "8 项设定", "7 个地图地点"],
  },
];

export function getStoryTemplate(templateId: StoryTemplateId): StoryTemplateDefinition {
  return storyTemplates.find((item) => item.id === templateId) ?? storyTemplates[0];
}

function resolveText(value: string | undefined, fallback: string): string {
  return value?.trim() || fallback;
}

function prose(lines: string[]): string {
  return lines.join("\n");
}

function createBlankProject(makeId: IdFactory, overrides: ProjectOverrides): StoryProject {
  const template = getStoryTemplate("blank");
  return {
    id: makeId("project"),
    name: resolveText(overrides.name, template.name),
    genre: resolveText(overrides.genre, template.genre),
    summary: resolveText(overrides.summary, template.summary),
    global_guidance: "",
    chapter_turns: 4,
    writing_style: "",
    polish_writing: true,
    style_example: "",
    style_notes: "",
    style_avoid: "",
    world: [],
    characters: [],
    map: {nodes: [], edges: []},
    chapters: [{id: makeId("chapter"), title: "第一章", content: ""}],
    chat: [],
    issues: [],
  };
}

function createGothicFantasyProject(makeId: IdFactory, overrides: ProjectOverrides): StoryProject {
  const template = getStoryTemplate("gothic-fantasy");
  const createdAt = new Date().toISOString();

  const saintCandleCity = makeId("map-node");
  const blackBellCathedral = makeId("map-node");
  const ashTunnel = makeId("map-node");
  const oldNightCourt = makeId("map-node");
  const mirrorLakeWood = makeId("map-node");
  const silentBorder = makeId("map-node");
  const boneRestInn = makeId("map-node");

  return {
    id: makeId("project"),
    name: resolveText(overrides.name, template.name),
    genre: resolveText(overrides.genre, template.genre),
    summary: resolveText(overrides.summary, template.summary),
    global_guidance:
      "围绕罗文与伊蕾娅被迫共生后的信任变化推进。教廷和夜裔都不能写成单一邪恶阵营；每次胜利都要带来新的伦理代价。逐步回收黑钟第十三响、灰烬名册和月冠空位三个谜团。",
    chapter_turns: 4,
    writing_style: "冷峻哥特，近距离第三人称",
    polish_writing: true,
    style_example:
      "雨水沿着银盔的裂纹流下，像一条迟到多年的泪痕。罗文没有抬头。黑钟正在云层后摆动，而整座圣烛城都假装听不见第十三响。",
    style_notes:
      "以罗文和伊蕾娅的有限视角交替叙事；用触觉、钟声、烛火和血液气味建立氛围；对话克制，情绪通过动作与选择显露。战斗段落使用短句，秘密揭示后留出安静反应。",
    style_avoid:
      "避免无代价的能力升级、脸谱化阵营、连续解释设定、现代网络用语和过度华丽的形容词。不要把月契写成方便的读心术。",
    world: [
      {
        id: makeId("world"),
        name: "圣烛城",
        type: "地点",
        summary: "永昼教廷统治的山巅圣城，终年以镜塔反射日光。",
        details:
          "城市分为上层圣环、骑士驻地和不见天光的灰巷。每晚宵禁前，黑钟大教堂会敲十二次；传说第十三响只为被历史抹去的人而鸣。",
        significance: "故事起点，也是灰烬战争真相被封存的地方。",
        tags: "圣城,教廷,黑钟,宵禁",
      },
      {
        id: makeId("world"),
        name: "永昼教廷",
        type: "势力",
        summary: "以保护人类为使命的宗教政权，掌握猎夜骑士团与镜焰术。",
        details:
          "教廷公开宣称夜裔没有灵魂，内部却以夜裔血液维持镜塔。温和派希望结束战争，烛座议会则准备举行名为‘永昼加冕’的秘密仪式。",
        significance: "罗文效忠的组织，也是制造月契实验的嫌疑者。",
        tags: "教廷,骑士团,镜焰,人类",
      },
      {
        id: makeId("world"),
        name: "夜冠议会",
        type: "势力",
        summary: "由七个夜裔家族组成的议会，在旧王失踪后共同摄政。",
        details:
          "七家表面承认伊蕾娅的继承权，实际都想控制月冠。议会成员受古老宾主律约束：在正式邀请进入的屋檐下不得先行伤害主人。",
        significance: "伊蕾娅的血统来源，也是追捕她的另一股力量。",
        tags: "夜裔,议会,王权,家族",
      },
      {
        id: makeId("world"),
        name: "伤月之契",
        type: "规则",
        summary: "让两名敌对血脉共享伤痛、梦境碎片和部分力量的禁忌契约。",
        details:
          "契约在黑月升起时增强。双方距离越远，伤口越难愈合；一方濒死时，另一方可以交出一段真实记忆换取其生机。契约不能传递完整思想，也不能强迫服从。",
        significance: "迫使罗文与伊蕾娅合作，并让每一次隐瞒都产生身体代价。",
        tags: "魔法,契约,共生,代价",
      },
      {
        id: makeId("world"),
        name: "灰烬战争",
        type: "历史",
        summary: "十二年前终结于无声边境的大火，双方都宣称是对方先毁约。",
        details:
          "战后所有阵亡者名册被教廷收走，夜裔旧王也在同一夜失踪。幸存者记得火焰没有温度，且曾同时照出太阳与黑月的影子。",
        significance: "罗文家人与伊蕾娅母亲的失踪都指向这场战争。",
        tags: "战争,旧案,焚城,失踪",
      },
      {
        id: makeId("world"),
        name: "月冠",
        type: "物品",
        summary: "夜裔王权的象征，据说能够命令血液记住真正的名字。",
        details:
          "月冠并非金属，而是七枚悬浮的黑色晶片。它只接受主动承担七家血债的人，因此继承王位等同于承受历代君主的伤痕与记忆。",
        significance: "伊蕾娅拒绝继位的根本原因，也是教廷仪式缺失的核心。",
        tags: "王冠,遗物,记忆,血债",
      },
      {
        id: makeId("world"),
        name: "镜湖林",
        type: "地点",
        summary: "生长着银叶树的中立森林，湖面会映出访客最不愿承认的身份。",
        details:
          "林中女巫遵循等价交换，不站在人类或夜裔一方。镜湖无法预言未来，只会把被篡改过的记忆恢复成互相矛盾的版本。",
        significance: "主角验证灰烬战争记忆、寻找解除月契方法的下一站。",
        tags: "森林,女巫,记忆,中立地",
      },
      {
        id: makeId("world"),
        name: "无声边境",
        type: "地点",
        summary: "灰烬战争后的封锁地带，声音会在越靠近中心时逐渐消失。",
        details:
          "中心保存着被烧成玻璃的城镇和一座没有入口的白塔。任何写下死者姓名的纸张都会在黎明前变为空白。",
        significance: "第一卷终点，埋藏旧王与永昼加冕的共同秘密。",
        tags: "边境,禁区,遗迹,终局地点",
      },
    ],
    characters: [
      {
        id: makeId("character"),
        name: "罗文·阿斯特",
        identity: "永昼教廷猎夜骑士",
        role: "主角",
        age: "27",
        stance: "守护平民，但不再盲信教廷",
        drive: "查清灰烬战争中家人死亡与教廷密令的真相",
        fear: "自己的正义只是别人手中的刀",
        traits: "克制,固执,观察敏锐,不善表达",
        abilities: "镜焰剑术,追踪血迹,短时抵抗夜裔魅惑",
        weakness: "月契会放大旧伤；无法对求饶者下杀手",
        secret: "他的骑士授勋记录比真实年龄早了三年，相关记忆可能被修改",
        speech: "句子短，先问事实；愤怒时反而使用完整敬语",
        appearance: "灰眼，黑发，左侧颈部有被银线缝合的旧伤，银甲刻满修补痕迹",
        background: "从灰烬战争遗址被教廷收养，十二年来一直追捕被定义为怪物的夜裔。",
        relationships: [
          {name: "伊蕾娅·诺克斯", relation: "被迫共生的敌人，逐渐成为唯一能验证彼此记忆的人"},
          {name: "玛格达·维恩", relation: "骑士团导师与监护人，忠诚正在发生冲突"},
        ],
        status: "受伤",
        notes: "第一视角之一；不能快速接受夜裔阵营。",
      },
      {
        id: makeId("character"),
        name: "伊蕾娅·诺克斯",
        identity: "失踪夜王的继承人",
        role: "主角",
        age: "23",
        stance: "反对教廷献祭，也拒绝成为七家的傀儡君主",
        drive: "找到母亲留下的灰烬名册，让战争双方承认被抹去的死者",
        fear: "戴上月冠后被历代君王的记忆吞没",
        traits: "机敏,骄傲,毒舌,珍惜承诺",
        abilities: "操纵血线,夜视,读取物品上残留的强烈情绪",
        weakness: "镜焰灼伤难以自愈；使用王血会短暂失去自己的记忆",
        secret: "她曾在十二年前的火场见过年幼的罗文，却记得他使用的是另一个名字",
        speech: "礼貌得近乎挑衅，极少直说关心；认真承诺时不用尊称",
        appearance: "银白长发，暗红瞳孔，右手戴着封印王血的黑丝手套",
        background: "在旧王失踪后被秘密送离王庭，多年来以古籍修复师身份调查战争记录。",
        relationships: [
          {name: "罗文·阿斯特", relation: "月契另一端；既是追捕者，也是逃离两大阵营的必要同盟"},
          {name: "弥拉·索瓦", relation: "掌握灰烬名册线索的旧识，彼此信任对方会遵守交易"},
        ],
        status: "被追捕",
        notes: "第一视角之一；王女身份不是性格的全部。",
      },
      {
        id: makeId("character"),
        name: "玛格达·维恩",
        identity: "猎夜骑士团副团长",
        role: "导师",
        age: "41",
        stance: "相信秩序必须被守住，但开始怀疑烛座议会",
        drive: "在教廷清洗行动前找到罗文并亲自问清他的选择",
        fear: "承认教廷犯错后，自己二十年的牺牲将失去意义",
        traits: "严厉,守诺,务实,保护欲强",
        abilities: "重剑格挡,镜盾结界,骑士团指挥",
        weakness: "旧日镜焰中毒使她无法长时间战斗",
        secret: "她亲手从灰烬名册上撕掉了罗文原来的那一页",
        speech: "像下达命令一样说话；只有称呼罗文全名时是在请求他",
        appearance: "短灰发，右眼为黄铜义眼，披风内侧缝着一枚烧焦的儿童徽章",
        background: "灰烬战争的教廷先锋，也是把罗文带回圣烛城的人。",
        relationships: [
          {name: "罗文·阿斯特", relation: "养育者与导师"},
          {name: "阿德里安·索恩", relation: "名义上的上级，彼此握有对方的旧案证据"},
        ],
        status: "正常",
        notes: "她应是可理解的制度维护者，而不是简单反派。",
      },
      {
        id: makeId("character"),
        name: "阿德里安·索恩",
        identity: "永昼教廷烛座主教",
        role: "反派",
        age: "56",
        stance: "认为永久结束种族战争比任何个人牺牲都重要",
        drive: "完成永昼加冕，让所有夜裔失去使用王血的能力",
        fear: "下一场战争会证明自己的残酷还不够彻底",
        traits: "温和,耐心,控制欲强,善于说服",
        abilities: "镜塔权限,仪式学,政治联盟",
        weakness: "无法直接使用镜焰；必须依赖骑士和仪式媒介",
        secret: "永昼加冕也会抹除所有参与者关于被献祭者的记忆",
        speech: "从不提高音量，总把命令说成替对方减轻负担的建议",
        appearance: "白金法衣没有任何装饰，手指常带清洗不掉的银灰",
        background: "经历两次边境屠杀后进入教廷核心，坚信可控的罪恶胜过无尽战争。",
        relationships: [
          {name: "玛格达·维恩", relation: "旧日战友与潜在告发者"},
          {name: "伊蕾娅·诺克斯", relation: "完成仪式所需的活体钥匙"},
        ],
        status: "正常",
        notes: "主要对手；动机成立，但手段不可被轻易合理化。",
      },
      {
        id: makeId("character"),
        name: "弥拉·索瓦",
        identity: "镜湖林的流亡女巫兼边境向导",
        role: "盟友",
        age: "31",
        stance: "拒绝替任何王权保守秘密，交易必须公开代价",
        drive: "找回被教廷没收的真实姓名，并终止无声边境的遗忘诅咒",
        fear: "恢复姓名时发现自己曾自愿参与月契实验",
        traits: "幽默,多疑,冷静,重视公平",
        abilities: "记忆辨伪,边境导航,封印术",
        weakness: "每次恢复他人记忆都会遗失自己一天的经历",
        secret: "她保管着灰烬名册的最后一张空白页",
        speech: "习惯先报价再回答，严肃时会把玩笑说完才行动",
        appearance: "褐色卷发，戴单片镜，腰间挂着装满无字纸条的玻璃瓶",
        background: "曾为教廷整理战争档案，发现记录被系统篡改后逃往镜湖林。",
        relationships: [
          {name: "伊蕾娅·诺克斯", relation: "互相利用的旧识"},
          {name: "罗文·阿斯特", relation: "知道他原名的线人，但拒绝免费告知"},
        ],
        status: "失踪",
        notes: "第二章结尾通过信物登场，第三章正式出现。",
      },
    ],
    map: {
      nodes: [
        {id: saintCandleCity, name: "圣烛城", x: 18, y: 22, description: "镜塔照耀的教廷都城"},
        {id: blackBellCathedral, name: "黑钟大教堂", x: 40, y: 16, description: "第十三响与秘密处刑场"},
        {id: ashTunnel, name: "灰烬隧道", x: 36, y: 46, description: "战争前连接城内外的废弃水道"},
        {id: oldNightCourt, name: "旧夜王庭", x: 72, y: 34, description: "无人继承的夜裔王宫"},
        {id: mirrorLakeWood, name: "镜湖林", x: 60, y: 72, description: "能映照矛盾记忆的中立森林"},
        {id: silentBorder, name: "无声边境", x: 88, y: 66, description: "灰烬战争留下的封锁遗址"},
        {id: boneRestInn, name: "眠骨驿站", x: 24, y: 76, description: "两族走私者共享的边境驿站"},
      ],
      edges: [
        {id: makeId("map-edge"), from: saintCandleCity, to: blackBellCathedral},
        {id: makeId("map-edge"), from: blackBellCathedral, to: ashTunnel},
        {id: makeId("map-edge"), from: ashTunnel, to: boneRestInn},
        {id: makeId("map-edge"), from: boneRestInn, to: mirrorLakeWood},
        {id: makeId("map-edge"), from: mirrorLakeWood, to: oldNightCourt},
        {id: makeId("map-edge"), from: oldNightCourt, to: silentBorder},
        {id: makeId("map-edge"), from: mirrorLakeWood, to: silentBorder},
      ],
    },
    chapters: [
      {
        id: makeId("chapter"),
        title: "序章 黑钟处刑",
        content: prose([
          "雨从圣烛城最高的镜塔上落下来时，已经带上了银灰色。",
          "",
          "罗文押着囚徒穿过十二道石阶。锁链的另一端系在少女腕上，黑色兜帽遮住她大半张脸，只有一缕银发被雨水贴在唇边。沿街的烛灯一盏接一盏熄灭，没有人愿意看夜裔的处刑，也没有人真的关上窗。",
          "",
          "‘你们的钟慢了。’囚徒忽然说。",
          "",
          "‘它从不慢。’罗文没有回头。",
          "",
          "‘那就是你们少记了一次。’",
          "",
          "黑钟大教堂近在雨幕之后。第一声钟鸣落下，石阶两侧的骑士同时举枪。罗文数到十二，押送队停在处刑门前。主教阿德里安站在门内，白金法衣没有沾上一滴水。",
          "",
          "‘辛苦了，罗文。把钥匙交给我。’",
          "",
          "钥匙。不是囚徒。罗文的手在剑柄上停了一瞬。",
          "",
          "少女轻轻笑了。她抬起被锁住的右手，黑丝手套下有暗红微光沿着血管游动。‘听见了吗，骑士？他从没打算审判我。’",
          "",
          "第十三声钟鸣从地下传来。",
          "",
          "所有烛火同时向下燃烧。罗文颈侧那道缝合多年的旧伤骤然裂开，而少女的脖颈也在同一位置渗出鲜血。两滴血落上锁链，银环像活物般收紧，将一轮残缺黑月烙进他们的皮肤。",
          "",
          "大教堂穹顶传来弓弦齐响。阿德里安退入门后，语气仍旧温和：‘不要让他们离开。仪式需要两个人都活着。’",
          "",
          "第一支箭刺入少女肩头。罗文却在自己的骨缝里感到了疼。",
          "",
          "他挥剑斩断锁链。",
          "",
          "那一刻，他背叛了教廷；也第一次听清了黑钟真正的声音。",
        ]),
      },
      {
        id: makeId("chapter"),
        title: "第一章 伤月之契",
        content: prose([
          "灰烬隧道比城里的墓穴更冷。罗文靠着湿墙坐下，把折断的箭杆从肩头拔出。伤口不在他身上，血却顺着他的指缝滴落。",
          "",
          "伊蕾娅隔着三步看他，像在观察一件终于证明会坏的盔甲。‘现在相信我没有对你下咒了？’",
          "",
          "‘我只相信伤口。’",
          "",
          "‘骑士的浪漫令人动容。’她扯开肩上的布料，箭伤边缘残留着镜焰的白光。‘这是伤月之契。旧王庭用它约束最不可信的盟友。你受我的疼痛，我承你的旧伤。我们离得越远，死得越快。’",
          "",
          "罗文用布带压住她的伤口。指尖接触的一刻，一段不属于他的记忆穿过脑海：没有温度的大火，哭喊却听不见声音；一个银发女人把孩子推向穿灰斗篷的骑士；孩子回头时，眼睛和罗文一样是灰色。",
          "",
          "他猛地收手。伊蕾娅也白了脸。",
          "",
          "‘你看见了什么？’两人同时问。",
          "",
          "隧道上方传来沉重脚步。猎夜骑士正在逐段封锁出口。罗文吹灭提灯，黑暗中只剩伊蕾娅的瞳孔微微发红。她没有趁机扑向他，反而把一枚细小的黑晶片塞进他手里。晶片一面刻着夜冠家徽，另一面却是教廷的镜塔。",
          "",
          "‘我进圣烛城不是为了刺杀主教。’她压低声音，‘我是来偷灰烬名册。十二年前死在无声边境的人，名字被你们从历史里删掉了。你的名字也在里面。’",
          "",
          "‘我的名字就在骑士名册上。’",
          "",
          "‘罗文·阿斯特在战争结束前三年已经受勋。那时你应该只有十二岁。’",
          "",
          "脚步停在拐角外。一个罗文熟悉的女声命令所有人卸下弩箭。",
          "",
          "‘罗文。’玛格达副团长隔着黑暗叫他的全名，‘把她交出来。我可以让今晚只剩一种真相。’",
          "",
          "伊蕾娅握紧他的手腕。月契在两人皮肤下同时发烫。罗文忽然明白，导师不是来抓捕他的。她是在请求他不要继续追问。",
        ]),
      },
      {
        id: makeId("chapter"),
        title: "第二章 没有主人的王座",
        content: prose([
          "旧夜王庭没有门。",
          "",
          "伊蕾娅领着罗文穿过一面覆满藤蔓的镜子，下一步便踩上积了十二年灰尘的红毯。月光从破碎穹顶垂落，照亮尽头那张空王座。七枚黑色晶片悬在王座上方，像一顶拒绝落下的王冠。",
          "",
          "‘你的议会很相信待客之道。’罗文看见两侧长桌已经坐满披着深色礼服的人。",
          "",
          "‘他们相信的是规则可以替他们杀人。’伊蕾娅松开他的手。离开半步，罗文肩头的伤便重新裂开。她只好又退回来，神情像吞下了一句脏话。",
          "",
          "摄政者赛勒斯从王座旁起身。他与伊蕾娅有相同的红眼睛，笑意却从未抵达眼底。‘欢迎回家，殿下。只要戴上月冠，议会会保护你的骑士。’",
          "",
          "‘他不是我的骑士。’",
          "",
          "‘契约不同意。’",
          "",
          "黑晶片随这句话轻轻旋转。无数陌生的伤痕同时从伊蕾娅手臂浮现。罗文听见她在月契另一端屏住呼吸，也听见王冠里层层叠叠的低语：继承不是命令别人，而是让死人住进自己的名字。",
          "",
          "长桌末端忽然有人推来一只玻璃瓶。瓶里装着一张空白纸条，封口处系着镜湖女巫的蓝线。",
          "",
          "‘弥拉送来的。’赛勒斯说，‘她愿意交出灰烬名册最后一页，条件是殿下今晚拒绝加冕。’",
          "",
          "议会席间响起压低的怒声。与此同时，王庭外传来镜焰炮装填的轰鸣。教廷比他们预想得更快。",
          "",
          "罗文拿起玻璃瓶。空白纸在他掌中渗出一行字，又迅速淡去。那不是罗文·阿斯特，而是一个他从未见过、身体却记得的名字。",
          "",
          "伊蕾娅也看见了。她第一次没有用嘲讽掩饰恐惧。",
          "",
          "‘十二年前，我在火场里见过你。’她说，‘可你当时已经死了。’",
          "",
          "王庭外，第一面镜墙被炮火照亮。王冠开始下降，教廷开始攻门，而空白纸上的名字只剩最后一个笔画。",
          "",
          "罗文必须在字迹消失前做出选择：护送伊蕾娅前往镜湖林，留下守住拒绝加冕的王庭，或者主动走向教廷，问玛格达自己究竟是谁。",
        ]),
      },
    ],
    chat: [],
    issues: [
      {
        id: makeId("issue"),
        kind: "提醒",
        item: "黑钟第十三响",
        reason: "已经在序章触发月契，但来源和敲钟者未知。",
        suggestion: "在第一卷中段提供一次错误解释，在无声边境揭示真正用途。",
        status: "待处理",
        created_at: createdAt,
      },
      {
        id: makeId("issue"),
        kind: "提醒",
        item: "罗文的原名与年龄",
        reason: "授勋年份、火场记忆和死亡记录互相矛盾。",
        suggestion: "让每个阵营掌握一部分真实记录，避免由单个角色一次性说明。",
        status: "待处理",
        created_at: createdAt,
      },
      {
        id: makeId("issue"),
        kind: "冲突",
        item: "王庭攻防后的路线",
        reason: "第二章结尾同时提供镜湖林、守城和返回教廷三条合理分支。",
        suggestion: "从本章末尾建立 AI 分支，比较三条路线对罗文与伊蕾娅关系的影响。",
        status: "待处理",
        created_at: createdAt,
      },
    ],
  };
}

export function createStoryProjectFromTemplate(
  templateId: StoryTemplateId,
  makeId: IdFactory,
  overrides: ProjectOverrides = {},
): StoryProject {
  if (templateId === "gothic-fantasy") {
    return createGothicFantasyProject(makeId, overrides);
  }
  return createBlankProject(makeId, overrides);
}
