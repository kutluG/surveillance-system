import React, { useState, useContext } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Switch,
  Alert,
  Modal,
  TextInput,
  Linking,
} from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { AuthContext } from '../contexts/AuthContext';
import { COLORS, SIZES, FONTS } from '../constants';
import Card from '../components/Card';
import Button from '../components/Button';

const SettingsScreen = ({ navigation }) => {
  const { logout, user } = useContext(AuthContext);
  
  const [settings, setSettings] = useState({
    notifications: {
      pushEnabled: true,
      soundEnabled: true,
      vibrationEnabled: true,
      motionAlerts: true,
      personAlerts: true,
      vehicleAlerts: true,
      systemAlerts: true,
    },
    privacy: {
      biometricLogin: false,
      autoLock: true,
      autoLockTime: 300, // 5 minutes
      hidePreview: false,
    },
    display: {
      darkTheme: true,
      fontSize: 'medium',
      showTimestamps: true,
      showCameraNames: true,
    },
    recording: {
      autoDownload: false,
      videoQuality: 'high',
      storageLimit: 500, // MB
      deleteAfterDays: 30,
    },
    network: {
      wifiOnly: false,
      lowDataMode: false,
      streamQuality: 'auto',
    },
  });

  const [profileModalVisible, setProfileModalVisible] = useState(false);
  const [changePasswordModalVisible, setChangePasswordModalVisible] = useState(false);
  const [aboutModalVisible, setAboutModalVisible] = useState(false);
  
  const [profileData, setProfileData] = useState({
    firstName: user?.firstName || '',
    lastName: user?.lastName || '',
    email: user?.email || '',
    phone: user?.phone || '',
  });

  const [passwordData, setPasswordData] = useState({
    currentPassword: '',
    newPassword: '',
    confirmPassword: '',
  });

  const handleSaveSettings = async () => {
    try {
      await AsyncStorage.setItem('@app_settings', JSON.stringify(settings));
      Alert.alert('Success', 'Settings saved successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to save settings');
    }
  };

  const handleResetSettings = () => {
    Alert.alert(
      'Reset Settings',
      'Are you sure you want to reset all settings to default?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Reset',
          style: 'destructive',
          onPress: () => {
            // Reset to default settings
            setSettings({
              notifications: {
                pushEnabled: true,
                soundEnabled: true,
                vibrationEnabled: true,
                motionAlerts: true,
                personAlerts: true,
                vehicleAlerts: true,
                systemAlerts: true,
              },
              privacy: {
                biometricLogin: false,
                autoLock: true,
                autoLockTime: 300,
                hidePreview: false,
              },
              display: {
                darkTheme: true,
                fontSize: 'medium',
                showTimestamps: true,
                showCameraNames: true,
              },
              recording: {
                autoDownload: false,
                videoQuality: 'high',
                storageLimit: 500,
                deleteAfterDays: 30,
              },
              network: {
                wifiOnly: false,
                lowDataMode: false,
                streamQuality: 'auto',
              },
            });
            Alert.alert('Success', 'Settings reset to default');
          },
        },
      ]
    );
  };

  const handleSaveProfile = async () => {
    try {
      // Here you would typically make an API call to update user profile
      // await userService.updateProfile(profileData);
      setProfileModalVisible(false);
      Alert.alert('Success', 'Profile updated successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to update profile');
    }
  };

  const handleChangePassword = async () => {
    if (passwordData.newPassword !== passwordData.confirmPassword) {
      Alert.alert('Error', 'New passwords do not match');
      return;
    }
    
    if (passwordData.newPassword.length < 8) {
      Alert.alert('Error', 'Password must be at least 8 characters');
      return;
    }

    try {
      // Here you would typically make an API call to change password
      // await authService.changePassword(passwordData);
      setChangePasswordModalVisible(false);
      setPasswordData({ currentPassword: '', newPassword: '', confirmPassword: '' });
      Alert.alert('Success', 'Password changed successfully');
    } catch (error) {
      Alert.alert('Error', 'Failed to change password');
    }
  };

  const handleLogout = () => {
    Alert.alert(
      'Logout',
      'Are you sure you want to logout?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Logout',
          style: 'destructive',
          onPress: logout,
        },
      ]
    );
  };

  const handleDeleteAccount = () => {
    Alert.alert(
      'Delete Account',
      'This action cannot be undone. All your data will be permanently deleted.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: () => {
            Alert.alert(
              'Are you absolutely sure?',
              'Type "DELETE" to confirm account deletion',
              [
                { text: 'Cancel', style: 'cancel' },
                {
                  text: 'Confirm',
                  style: 'destructive',
                  onPress: async () => {
                    try {
                      // Here you would make an API call to delete the account
                      // await userService.deleteAccount();
                      logout();
                    } catch (error) {
                      Alert.alert('Error', 'Failed to delete account');
                    }
                  },
                },
              ]
            );
          },
        },
      ]
    );
  };

  const renderProfileModal = () => (
    <Modal
      visible={profileModalVisible}
      transparent
      animationType="slide"
      onRequestClose={() => setProfileModalVisible(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>Edit Profile</Text>
          
          <ScrollView style={styles.modalScroll}>
            <View style={styles.inputSection}>
              <Text style={styles.inputLabel}>First Name</Text>
              <TextInput
                style={styles.input}
                value={profileData.firstName}
                onChangeText={(text) => setProfileData({ ...profileData, firstName: text })}
                placeholder="Enter first name"
                placeholderTextColor={COLORS.textSecondary}
              />
            </View>

            <View style={styles.inputSection}>
              <Text style={styles.inputLabel}>Last Name</Text>
              <TextInput
                style={styles.input}
                value={profileData.lastName}
                onChangeText={(text) => setProfileData({ ...profileData, lastName: text })}
                placeholder="Enter last name"
                placeholderTextColor={COLORS.textSecondary}
              />
            </View>

            <View style={styles.inputSection}>
              <Text style={styles.inputLabel}>Email</Text>
              <TextInput
                style={styles.input}
                value={profileData.email}
                onChangeText={(text) => setProfileData({ ...profileData, email: text })}
                placeholder="Enter email"
                placeholderTextColor={COLORS.textSecondary}
                keyboardType="email-address"
                autoCapitalize="none"
              />
            </View>

            <View style={styles.inputSection}>
              <Text style={styles.inputLabel}>Phone</Text>
              <TextInput
                style={styles.input}
                value={profileData.phone}
                onChangeText={(text) => setProfileData({ ...profileData, phone: text })}
                placeholder="Enter phone number"
                placeholderTextColor={COLORS.textSecondary}
                keyboardType="phone-pad"
              />
            </View>
          </ScrollView>

          <View style={styles.modalButtons}>
            <Button
              title="Cancel"
              variant="outline"
              onPress={() => setProfileModalVisible(false)}
              style={styles.modalButton}
            />
            <Button
              title="Save"
              onPress={handleSaveProfile}
              style={styles.modalButton}
            />
          </View>
        </View>
      </View>
    </Modal>
  );

  const renderChangePasswordModal = () => (
    <Modal
      visible={changePasswordModalVisible}
      transparent
      animationType="slide"
      onRequestClose={() => setChangePasswordModalVisible(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>Change Password</Text>
          
          <ScrollView style={styles.modalScroll}>
            <View style={styles.inputSection}>
              <Text style={styles.inputLabel}>Current Password</Text>
              <TextInput
                style={styles.input}
                value={passwordData.currentPassword}
                onChangeText={(text) => setPasswordData({ ...passwordData, currentPassword: text })}
                placeholder="Enter current password"
                placeholderTextColor={COLORS.textSecondary}
                secureTextEntry
              />
            </View>

            <View style={styles.inputSection}>
              <Text style={styles.inputLabel}>New Password</Text>
              <TextInput
                style={styles.input}
                value={passwordData.newPassword}
                onChangeText={(text) => setPasswordData({ ...passwordData, newPassword: text })}
                placeholder="Enter new password"
                placeholderTextColor={COLORS.textSecondary}
                secureTextEntry
              />
            </View>

            <View style={styles.inputSection}>
              <Text style={styles.inputLabel}>Confirm New Password</Text>
              <TextInput
                style={styles.input}
                value={passwordData.confirmPassword}
                onChangeText={(text) => setPasswordData({ ...passwordData, confirmPassword: text })}
                placeholder="Confirm new password"
                placeholderTextColor={COLORS.textSecondary}
                secureTextEntry
              />
            </View>
          </ScrollView>

          <View style={styles.modalButtons}>
            <Button
              title="Cancel"
              variant="outline"
              onPress={() => setChangePasswordModalVisible(false)}
              style={styles.modalButton}
            />
            <Button
              title="Change"
              onPress={handleChangePassword}
              style={styles.modalButton}
            />
          </View>
        </View>
      </View>
    </Modal>
  );

  const renderAboutModal = () => (
    <Modal
      visible={aboutModalVisible}
      transparent
      animationType="slide"
      onRequestClose={() => setAboutModalVisible(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>About</Text>
          
          <ScrollView style={styles.modalScroll}>
            <View style={styles.aboutSection}>
              <Text style={styles.appName}>AI Surveillance System</Text>
              <Text style={styles.appVersion}>Version 1.0.0</Text>
              <Text style={styles.appDescription}>
                Advanced surveillance system with AI-powered detection capabilities, 
                real-time monitoring, and intelligent alerts.
              </Text>
            </View>

            <View style={styles.aboutSection}>
              <Text style={styles.aboutLabel}>Features:</Text>
              <Text style={styles.aboutText}>• Real-time camera monitoring</Text>
              <Text style={styles.aboutText}>• AI-powered object detection</Text>
              <Text style={styles.aboutText}>• Motion and person detection</Text>
              <Text style={styles.aboutText}>• Push notifications</Text>
              <Text style={styles.aboutText}>• Cloud recording</Text>
            </View>

            <View style={styles.aboutSection}>
              <TouchableOpacity
                style={styles.linkButton}
                onPress={() => Linking.openURL('https://example.com/privacy')}
              >
                <Text style={styles.linkText}>Privacy Policy</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={styles.linkButton}
                onPress={() => Linking.openURL('https://example.com/terms')}
              >
                <Text style={styles.linkText}>Terms of Service</Text>
              </TouchableOpacity>
              
              <TouchableOpacity
                style={styles.linkButton}
                onPress={() => Linking.openURL('https://example.com/support')}
              >
                <Text style={styles.linkText}>Support</Text>
              </TouchableOpacity>
            </View>
          </ScrollView>

          <View style={styles.modalButtons}>
            <Button
              title="Close"
              onPress={() => setAboutModalVisible(false)}
              style={styles.fullWidthButton}
            />
          </View>
        </View>
      </View>
    </Modal>
  );

  return (
    <ScrollView style={styles.container}>
      {/* User Profile */}
      <Card style={styles.profileCard}>
        <Text style={styles.sectionTitle}>Profile</Text>
        <View style={styles.profileInfo}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>
              {user?.firstName?.charAt(0) || 'U'}
            </Text>
          </View>
          <View style={styles.userInfo}>
            <Text style={styles.userName}>
              {user?.firstName} {user?.lastName}
            </Text>
            <Text style={styles.userEmail}>{user?.email}</Text>
          </View>
        </View>
        <View style={styles.profileActions}>
          <Button
            title="Edit Profile"
            variant="outline"
            size="small"
            onPress={() => setProfileModalVisible(true)}
            style={styles.profileButton}
          />
          <Button
            title="Change Password"
            variant="outline"
            size="small"
            onPress={() => setChangePasswordModalVisible(true)}
            style={styles.profileButton}
          />
        </View>
      </Card>

      {/* Notifications */}
      <Card style={styles.settingsCard}>
        <Text style={styles.sectionTitle}>Notifications</Text>
        
        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>Push Notifications</Text>
          <Switch
            value={settings.notifications.pushEnabled}
            onValueChange={(value) => 
              setSettings({
                ...settings,
                notifications: { ...settings.notifications, pushEnabled: value }
              })
            }
            trackColor={{ false: COLORS.border, true: COLORS.primary }}
          />
        </View>

        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>Sound</Text>
          <Switch
            value={settings.notifications.soundEnabled}
            onValueChange={(value) => 
              setSettings({
                ...settings,
                notifications: { ...settings.notifications, soundEnabled: value }
              })
            }
            trackColor={{ false: COLORS.border, true: COLORS.primary }}
          />
        </View>

        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>Vibration</Text>
          <Switch
            value={settings.notifications.vibrationEnabled}
            onValueChange={(value) => 
              setSettings({
                ...settings,
                notifications: { ...settings.notifications, vibrationEnabled: value }
              })
            }
            trackColor={{ false: COLORS.border, true: COLORS.primary }}
          />
        </View>

        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>Motion Alerts</Text>
          <Switch
            value={settings.notifications.motionAlerts}
            onValueChange={(value) => 
              setSettings({
                ...settings,
                notifications: { ...settings.notifications, motionAlerts: value }
              })
            }
            trackColor={{ false: COLORS.border, true: COLORS.primary }}
          />
        </View>

        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>Person Detection Alerts</Text>
          <Switch
            value={settings.notifications.personAlerts}
            onValueChange={(value) => 
              setSettings({
                ...settings,
                notifications: { ...settings.notifications, personAlerts: value }
              })
            }
            trackColor={{ false: COLORS.border, true: COLORS.primary }}
          />
        </View>
      </Card>

      {/* Privacy & Security */}
      <Card style={styles.settingsCard}>
        <Text style={styles.sectionTitle}>Privacy & Security</Text>
        
        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>Biometric Login</Text>
          <Switch
            value={settings.privacy.biometricLogin}
            onValueChange={(value) => 
              setSettings({
                ...settings,
                privacy: { ...settings.privacy, biometricLogin: value }
              })
            }
            trackColor={{ false: COLORS.border, true: COLORS.primary }}
          />
        </View>

        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>Auto Lock</Text>
          <Switch
            value={settings.privacy.autoLock}
            onValueChange={(value) => 
              setSettings({
                ...settings,
                privacy: { ...settings.privacy, autoLock: value }
              })
            }
            trackColor={{ false: COLORS.border, true: COLORS.primary }}
          />
        </View>

        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>Hide Notification Previews</Text>
          <Switch
            value={settings.privacy.hidePreview}
            onValueChange={(value) => 
              setSettings({
                ...settings,
                privacy: { ...settings.privacy, hidePreview: value }
              })
            }
            trackColor={{ false: COLORS.border, true: COLORS.primary }}
          />
        </View>
      </Card>

      {/* Display */}
      <Card style={styles.settingsCard}>
        <Text style={styles.sectionTitle}>Display</Text>
        
        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>Dark Theme</Text>
          <Switch
            value={settings.display.darkTheme}
            onValueChange={(value) => 
              setSettings({
                ...settings,
                display: { ...settings.display, darkTheme: value }
              })
            }
            trackColor={{ false: COLORS.border, true: COLORS.primary }}
          />
        </View>

        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>Show Timestamps</Text>
          <Switch
            value={settings.display.showTimestamps}
            onValueChange={(value) => 
              setSettings({
                ...settings,
                display: { ...settings.display, showTimestamps: value }
              })
            }
            trackColor={{ false: COLORS.border, true: COLORS.primary }}
          />
        </View>

        <View style={styles.settingItem}>
          <Text style={styles.settingLabel}>Show Camera Names</Text>
          <Switch
            value={settings.display.showCameraNames}
            onValueChange={(value) => 
              setSettings({
                ...settings,
                display: { ...settings.display, showCameraNames: value }
              })
            }
            trackColor={{ false: COLORS.border, true: COLORS.primary }}
          />
        </View>
      </Card>

      {/* Actions */}
      <Card style={styles.actionsCard}>
        <Button
          title="Save Settings"
          onPress={handleSaveSettings}
          style={styles.actionButton}
        />
        <Button
          title="Reset to Default"
          variant="outline"
          onPress={handleResetSettings}
          style={styles.actionButton}
        />
        <Button
          title="About"
          variant="outline"
          onPress={() => setAboutModalVisible(true)}
          style={styles.actionButton}
        />
        <Button
          title="Logout"
          variant="outline"
          onPress={handleLogout}
          style={styles.actionButton}
        />
        <Button
          title="Delete Account"
          variant="danger"
          onPress={handleDeleteAccount}
          style={styles.actionButton}
        />
      </Card>

      {renderProfileModal()}
      {renderChangePasswordModal()}
      {renderAboutModal()}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: COLORS.background,
  },
  profileCard: {
    margin: SIZES.margin,
    padding: SIZES.padding,
  },
  sectionTitle: {
    color: COLORS.text,
    ...FONTS.h3,
    fontWeight: 'bold',
    marginBottom: SIZES.margin,
  },
  profileInfo: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SIZES.margin,
  },
  avatar: {
    width: 60,
    height: 60,
    borderRadius: 30,
    backgroundColor: COLORS.primary,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: SIZES.margin,
  },
  avatarText: {
    color: COLORS.white,
    ...FONTS.h2,
    fontWeight: 'bold',
  },
  userInfo: {
    flex: 1,
  },
  userName: {
    color: COLORS.text,
    ...FONTS.h4,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  userEmail: {
    color: COLORS.textSecondary,
    ...FONTS.body4,
  },
  profileActions: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  profileButton: {
    flex: 1,
    marginHorizontal: SIZES.margin / 2,
  },
  settingsCard: {
    margin: SIZES.margin,
    marginTop: 0,
    padding: SIZES.padding,
  },
  settingItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.margin,
  },
  settingLabel: {
    color: COLORS.text,
    ...FONTS.body3,
    flex: 1,
  },
  actionsCard: {
    margin: SIZES.margin,
    marginTop: 0,
    padding: SIZES.padding,
  },
  actionButton: {
    marginBottom: SIZES.margin,
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius * 2,
    width: '90%',
    maxHeight: '80%',
  },
  modalTitle: {
    color: COLORS.text,
    ...FONTS.h3,
    fontWeight: 'bold',
    textAlign: 'center',
    padding: SIZES.padding,
    borderBottomWidth: 1,
    borderBottomColor: COLORS.border,
  },
  modalScroll: {
    maxHeight: 400,
    padding: SIZES.padding,
  },
  inputSection: {
    marginBottom: SIZES.margin,
  },
  inputLabel: {
    color: COLORS.text,
    ...FONTS.body3,
    fontWeight: 'bold',
    marginBottom: SIZES.margin / 2,
  },
  input: {
    backgroundColor: COLORS.background,
    borderRadius: SIZES.radius,
    padding: SIZES.padding,
    color: COLORS.text,
    ...FONTS.body4,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  modalButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: SIZES.padding,
    borderTopWidth: 1,
    borderTopColor: COLORS.border,
  },
  modalButton: {
    flex: 1,
    marginHorizontal: SIZES.margin / 2,
  },
  fullWidthButton: {
    width: '100%',
  },
  aboutSection: {
    marginBottom: SIZES.margin * 1.5,
  },
  appName: {
    color: COLORS.text,
    ...FONTS.h2,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: SIZES.margin / 2,
  },
  appVersion: {
    color: COLORS.textSecondary,
    ...FONTS.body3,
    textAlign: 'center',
    marginBottom: SIZES.margin,
  },
  appDescription: {
    color: COLORS.text,
    ...FONTS.body4,
    textAlign: 'center',
    lineHeight: 20,
  },
  aboutLabel: {
    color: COLORS.text,
    ...FONTS.body3,
    fontWeight: 'bold',
    marginBottom: SIZES.margin / 2,
  },
  aboutText: {
    color: COLORS.textSecondary,
    ...FONTS.body4,
    marginBottom: 4,
  },
  linkButton: {
    paddingVertical: SIZES.padding / 2,
  },
  linkText: {
    color: COLORS.primary,
    ...FONTS.body3,
    textDecorationLine: 'underline',
  },
});

export default SettingsScreen;
