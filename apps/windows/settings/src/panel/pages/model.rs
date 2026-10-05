//! 「本地模型」页：保留现有随包整句模型开关。

use windows_reactor::*;

use crate::panel::controls::{field, page};
use crate::panel::{Message, Settings};

pub(crate) fn view(settings: &Settings, context: &mut ViewContext<Settings>) -> View {
    let local_model = field(
        "本地整句模型",
        "随包的小模型在本机给整句候选重新排序，全程离线；停键后几十毫秒生效。关掉只用词库统计。",
        ToggleSwitch::new()
            .is_on(settings.config.model.enabled)
            .on_toggled(context.callback(Message::LocalModel)),
    );
    page("本地模型", StackPanel::new().spacing(16.0).children([local_model]))
}
