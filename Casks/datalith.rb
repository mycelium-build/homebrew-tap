cask "datalith" do
  arch arm: "aarch64", intel: "x64"

  version "1.1.1"
  sha256 arm:   "82222e21104a7a344bcb8d9ae45670645e7ba60a3015b4e514d91d04c32b4549",
         intel: "2e2f5e7383dd391975cc2ceda803c08d04c094b771175df86bbf3a9f29b8e148"

  url "https://github.com/mycelium-build/datalith-app/releases/download/v#{version}/Datalith_#{version}_#{arch}.dmg"
  name "Datalith"
  desc "Local-first knowledge workspace"
  homepage "https://datalith.work/"

  livecheck do
    url "https://updates.datalith.work/stable"
    strategy :json do |json|
      json["version"] if json["version"] != "0.0.0"
    end
  end

  auto_updates true
  depends_on :macos

  app "Datalith.app"

  uninstall quit: "build.mycelium.datalith"
end
