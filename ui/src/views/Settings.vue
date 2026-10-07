<!--
  Copyright (C) 2023 Nethesis S.r.l.
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <cv-grid fullWidth>
    <cv-row>
      <cv-column class="page-title">
        <h2>{{ $t("settings.title") }}</h2>
      </cv-column>
    </cv-row>
    <cv-row v-if="error.getConfiguration">
      <cv-column>
        <NsInlineNotification
          kind="error"
          :title="$t('action.get-configuration')"
          :description="error.getConfiguration"
          :showCloseButton="false"
        />
      </cv-column>
    </cv-row>
    <cv-row>
      <cv-column>
        <cv-tile light>
          <cv-row v-if="fqdn">
            <cv-column>
              <p>
                {{ $t("settings.access_url") }}
                <cv-link :href="bbsUrl" target="_blank">{{ bbsUrl }}</cv-link>
              </p>
            </cv-column>
          </cv-row>
          <cv-form @submit.prevent="configureModule">
            <NsTextInput
              :label="$t('settings.fqdn')"
              v-model="fqdn"
              placeholder="bbs.example.com"
              :helper-text="$t('settings.fqdn_help')"
              :disabled="loading.getConfiguration || loading.configureModule"
              :invalid-message="error.fqdn"
              ref="fqdn"
            />
            <NsToggle
              v-model="letsEncrypt"
              :label="$t('settings.lets_encrypt')"
              value="lets-encrypt"
              :disabled="loading.getConfiguration || loading.configureModule"
            >
              <template slot="text-left">{{ $t("settings.disabled") }}</template>
              <template slot="text-right">{{ $t("settings.enabled") }}</template>
              <template slot="tooltip">{{ $t("settings.tls_help") }}</template>
            </NsToggle>
            <NsTextInput
              :label="$t('settings.ssh_port')"
              v-model="sshPort"
              type="number"
              min="1024"
              max="65535"
              :helper-text="$t('settings.ssh_port_help')"
              :disabled="loading.getConfiguration || loading.configureModule"
              :invalid-message="error.ssh_port"
              ref="ssh_port"
            />
            <NsPasswordInput
              :label="$t('settings.admin_password')"
              v-model="adminPassword"
              :helper-text="
                $t(
                  adminPasswordInitialized
                    ? 'settings.admin_password_initialized'
                    : 'settings.admin_password_help'
                )
              "
              :disabled="
                loading.getConfiguration ||
                loading.configureModule ||
                adminPasswordInitialized
              "
              :invalid-message="error.admin_password"
              ref="admin_password"
            />
            <cv-row v-if="error.configureModule">
              <cv-column>
                <NsInlineNotification
                  kind="error"
                  :title="$t('action.configure-module')"
                  :description="error.configureModule"
                  :showCloseButton="false"
                />
              </cv-column>
            </cv-row>
            <NsButton
              kind="primary"
              :icon="Save20"
              :loading="loading.configureModule"
              :disabled="loading.getConfiguration || loading.configureModule"
              >{{ $t("settings.save") }}</NsButton
            >
          </cv-form>
        </cv-tile>
      </cv-column>
    </cv-row>
  </cv-grid>
</template>

<script>
import to from "await-to-js";
import { mapState } from "vuex";
import {
  QueryParamService,
  UtilService,
  TaskService,
  IconService,
  PageTitleService,
} from "@nethserver/ns8-ui-lib";

export default {
  name: "Settings",
  mixins: [
    TaskService,
    IconService,
    UtilService,
    QueryParamService,
    PageTitleService,
  ],
  pageTitle() {
    return this.$t("settings.title") + " - " + this.appName;
  },
  data() {
    return {
      q: {
        page: "settings",
      },
      urlCheckInterval: null,
      fqdn: "",
      letsEncrypt: false,
      sshPort: "2222",
      adminPassword: "",
      adminPasswordInitialized: false,
      loading: {
        getConfiguration: false,
        configureModule: false,
      },
      error: {
        getConfiguration: "",
        configureModule: "",
        fqdn: "",
        ssh_port: "",
        admin_password: "",
      },
    };
  },
  computed: {
    ...mapState(["instanceName", "core", "appName"]),
    bbsUrl() {
      return this.fqdn ? "https://" + this.fqdn : "";
    },
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      vm.watchQueryData(vm);
      vm.urlCheckInterval = vm.initUrlBindingForApp(vm, vm.q.page);
    });
  },
  beforeRouteLeave(to, from, next) {
    clearInterval(this.urlCheckInterval);
    next();
  },
  created() {
    this.getConfiguration();
  },
  methods: {
    async getConfiguration() {
      this.loading.getConfiguration = true;
      this.error.getConfiguration = "";
      const taskAction = "get-configuration";
      const eventId = this.getUuid();

      // register to task error
      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.getConfigurationAborted
      );

      // register to task completion
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        this.getConfigurationCompleted
      );

      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          extra: {
            title: this.$t("action." + taskAction),
            isNotificationHidden: true,
            eventId,
          },
        })
      );
      const err = res[0];

      if (err) {
        console.error(`error creating task ${taskAction}`);
        this.error.getConfiguration = this.getErrorMessage(err);
        this.loading.getConfiguration = false;
        return;
      }
    },
    getConfigurationAborted(taskResult, taskContext) {
      console.error(`${taskContext.action} aborted`, taskResult);
      this.error.getConfiguration = this.$t("error.generic_error");
      this.loading.getConfiguration = false;
    },
    getConfigurationCompleted(taskContext, taskResult) {
      this.loading.getConfiguration = false;
      const config = taskResult.output;

      this.fqdn = config.fqdn || "";
      this.letsEncrypt = config.lets_encrypt;
      this.sshPort = String(config.ssh_port || 2222);
      this.adminPasswordInitialized = config.admin_password_initialized === true;
      this.adminPassword = "";
      this.focusElement("fqdn");
    },
    validateConfigureModule() {
      this.clearErrors(this);
      let isValidationOk = true;

      const fqdnPattern = /^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))+$/i;
      if (!fqdnPattern.test(this.fqdn.trim())) {
        this.error.fqdn = this.$t("settings.invalid_fqdn");
        this.focusElement("fqdn");
        isValidationOk = false;
      }

      const port = Number(this.sshPort);
      if (!Number.isInteger(port) || port < 1024 || port > 65535) {
        this.error.ssh_port = this.$t("settings.invalid_ssh_port");
        if (isValidationOk) {
          this.focusElement("ssh_port");
        }
        isValidationOk = false;
      }

      if (
        !this.adminPasswordInitialized &&
        this.adminPassword &&
        (this.adminPassword.length < 8 ||
          this.adminPassword.length > 128 ||
          /[\r\n\u0000]/.test(this.adminPassword))
      ) {
        this.error.admin_password = this.$t("settings.invalid_admin_password");
        if (isValidationOk) {
          this.focusElement("admin_password");
        }
        isValidationOk = false;
      }
      return isValidationOk;
    },
    configureModuleValidationFailed(validationErrors) {
      this.loading.configureModule = false;
      let focusAlreadySet = false;

      for (const validationError of validationErrors) {
        const field = validationError.field;

        if (field !== "(root)") {
          // set i18n error message
          this.error[field] = this.$t("settings." + validationError.error);
          if (
            field === "admin_password" &&
            validationError.error === "admin_password_already_initialized"
          ) {
            this.adminPasswordInitialized = true;
            this.adminPassword = "";
          }

          if (!focusAlreadySet) {
            this.focusElement(field);
            focusAlreadySet = true;
          }
        }
      }
    },
    async configureModule() {
      const isValidationOk = this.validateConfigureModule();
      if (!isValidationOk) {
        return;
      }

      this.loading.configureModule = true;
      const taskAction = "configure-module";
      const eventId = this.getUuid();

      // register to task error
      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.configureModuleAborted
      );

      // register to task validation
      this.core.$root.$once(
        `${taskAction}-validation-failed-${eventId}`,
        this.configureModuleValidationFailed
      );

      // register to task completion
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        this.configureModuleCompleted
      );

      const data = {
        fqdn: this.fqdn.trim().toLowerCase(),
        lets_encrypt: this.letsEncrypt,
        ssh_port: Number(this.sshPort),
      };
      if (!this.adminPasswordInitialized && this.adminPassword) {
        data.admin_password = this.adminPassword;
      }

      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          data,
          extra: {
            title: this.$t("settings.configure_instance", {
              instance: this.instanceName,
            }),
            description: this.$t("common.processing"),
            eventId,
          },
        })
      );
      const err = res[0];

      if (!err) {
        this.adminPassword = "";
      }

      if (err) {
        console.error(`error creating task ${taskAction}`);
        this.error.configureModule = this.getErrorMessage(err);
        this.loading.configureModule = false;
        return;
      }
    },
    configureModuleAborted(...args) {
      console.error(`${args[1].action} aborted`);
      this.error.configureModule = this.$t("error.generic_error");
      this.loading.configureModule = false;
      this.getConfiguration();
    },
    configureModuleCompleted() {
      this.loading.configureModule = false;

      // reload configuration
      this.getConfiguration();
    },
  },
};
</script>

<style scoped lang="scss">
@import "../styles/carbon-utils";
</style>
