//! 旧版联网配置不能在离线应用中恢复网络能力，本地设置继续解析。

use qingjian_platform::Config;

#[test]
fn legacy_network_configuration_is_ignored() {
    let path = std::env::temp_dir().join(format!("qingjian-offline-{}.toml", std::process::id()));
    std::fs::write(
        &path,
        r#"
[predict]
enabled = true
base_url = "https://api.deepseek.com"
api_key = "test-only"
[update]
check = true
channel = "beta"
[model]
enabled = false
[general]
page_size = 5
"#,
    )
    .unwrap();
    let config = Config::load(&path).unwrap();
    std::fs::remove_file(path).unwrap();
    assert!(!config.model.enabled);
    assert_eq!(config.general.page_size, 5);
    let serialized = toml::to_string(&config).unwrap();
    for removed in ["[predict]", "[update]", "base_url", "api_key"] {
        assert!(!serialized.contains(removed), "{serialized}");
    }
}
