import { ElAlert } from "element-plus/es/components/alert/index.mjs";
import { ElButton } from "element-plus/es/components/button/index.mjs";
import { ElCard } from "element-plus/es/components/card/index.mjs";
import { ElCol } from "element-plus/es/components/col/index.mjs";
import {
  ElDescriptions,
  ElDescriptionsItem,
} from "element-plus/es/components/descriptions/index.mjs";
import { ElDialog } from "element-plus/es/components/dialog/index.mjs";
import { ElDrawer } from "element-plus/es/components/drawer/index.mjs";
import { ElEmpty } from "element-plus/es/components/empty/index.mjs";
import {
  ElForm,
  ElFormItem,
} from "element-plus/es/components/form/index.mjs";
import { ElInput } from "element-plus/es/components/input/index.mjs";
import { ElInputNumber } from "element-plus/es/components/input-number/index.mjs";
import { ElOption, ElSelect } from "element-plus/es/components/select/index.mjs";
import { ElRadio, ElRadioButton, ElRadioGroup } from "element-plus/es/components/radio/index.mjs";
import { ElRow } from "element-plus/es/components/row/index.mjs";
import { ElScrollbar } from "element-plus/es/components/scrollbar/index.mjs";
import { ElSpace } from "element-plus/es/components/space/index.mjs";
import { ElSlider } from "element-plus/es/components/slider/index.mjs";
import { ElSwitch } from "element-plus/es/components/switch/index.mjs";
import { ElTable, ElTableColumn } from "element-plus/es/components/table/index.mjs";
import { ElTabs, ElTabPane } from "element-plus/es/components/tabs/index.mjs";
import { ElTag } from "element-plus/es/components/tag/index.mjs";
import "element-plus/dist/index.css";
import "element-plus/theme-chalk/dark/css-vars.css";

import { createApp } from "vue";

import App from "./App.vue";
import "./styles.css";

const app = createApp(App);

[
  ElAlert,
  ElButton,
  ElCard,
  ElCol,
  ElDescriptions,
  ElDescriptionsItem,
  ElDialog,
  ElDrawer,
  ElEmpty,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElOption,
  ElRadio,
  ElRadioButton,
  ElRadioGroup,
  ElRow,
  ElScrollbar,
  ElSelect,
  ElSlider,
  ElSpace,
  ElSwitch,
  ElTable,
  ElTableColumn,
  ElTabs,
  ElTabPane,
  ElTag,
].forEach((component) => {
  app.use(component);
});

app.mount("#app");
