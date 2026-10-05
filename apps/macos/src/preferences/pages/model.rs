//! 「本地模型」页：保留随包整句模型开关。

use objc2::MainThreadMarker;
use objc2::rc::Retained;
use objc2_app_kit::NSButton;
use qingjian_platform::Config;

use crate::preferences::controls::{checkbox, note, row_checkbox, set_checked};
use crate::preferences::layout::Layout;
use crate::preferences::setting::Setting;
use crate::preferences::target::PreferencesTarget;

pub struct ModelPage {
    /// 本地整句模型开关。
    local_model: Retained<NSButton>,
}

impl ModelPage {
    pub fn build(layout: &mut Layout, mtm: MainThreadMarker, target: &PreferencesTarget) -> Self {
        let local_model = checkbox(mtm, "本地整句模型", Setting::LocalModelEnabled, target);
        row_checkbox(layout, &local_model);
        note(layout, mtm, "随包的小模型在本机给整句候选重新排序，全程离线；停键后几十毫秒生效。关掉只用词库统计。");
        Self { local_model }
    }

    pub fn sync(&self, config: &Config, model_present: bool) {
        set_checked(&self.local_model, config.model.enabled && model_present);
        self.local_model.setEnabled(model_present);
    }
}
