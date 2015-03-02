$: << 'cf_spec'
require 'cf_spec_helper'

describe 'CF PHP Buildpack with Lucid rootfs' do
  subject(:app) { Machete.deploy_app(app_name) }
  let(:browser) { Machete::Browser.new(app) }

  after do
    # Machete::CF::DeleteApp.new.execute(app)
  end

  context 'deploying a basic PHP app', if: ENV['CF_STACK'] == 'lucid' do
    let(:app_name) { 'php_app' }

    specify do
      expect(app).to be_running

      expect(app).to have_logged 'lucid'
    end
  end

  context 'deploying a basic PHP app', if: ENV['CF_STACK'] == 'trusty' do
    let(:app_name) { 'php_app' }

    specify do
      expect(app).to be_running

      expect(app).to have_logged 'trusty'
    end
  end
end
