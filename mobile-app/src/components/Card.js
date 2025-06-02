import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import { COLORS, SIZES, FONTS } from '../constants';

const Card = ({ 
  children, 
  title, 
  subtitle,
  icon,
  iconColor,
  style,
  headerStyle,
  contentStyle,
  onPress,
  ...props 
}) => {
  const CardComponent = onPress ? TouchableOpacity : View;

  return (
    <CardComponent 
      style={[styles.card, style]}
      onPress={onPress}
      activeOpacity={onPress ? 0.7 : 1}
      {...props}
    >
      {(title || subtitle || icon) && (
        <View style={[styles.header, headerStyle]}>
          {icon && (
            <Icon 
              name={icon} 
              size={24} 
              color={iconColor || COLORS.primary} 
              style={styles.icon} 
            />
          )}
          <View style={styles.headerText}>
            {title && <Text style={styles.title}>{title}</Text>}
            {subtitle && <Text style={styles.subtitle}>{subtitle}</Text>}
          </View>
        </View>
      )}
      <View style={[styles.content, contentStyle]}>
        {children}
      </View>
    </CardComponent>
  );
};

const StatCard = ({ 
  title, 
  value, 
  icon, 
  iconColor, 
  change, 
  changeType,
  onPress,
  style 
}) => {
  const getChangeColor = () => {
    switch (changeType) {
      case 'positive': return COLORS.success;
      case 'negative': return COLORS.error;
      default: return COLORS.gray;
    }
  };

  const getChangeIcon = () => {
    switch (changeType) {
      case 'positive': return 'trending-up';
      case 'negative': return 'trending-down';
      default: return 'trending-flat';
    }
  };

  return (
    <Card 
      style={[styles.statCard, style]}
      onPress={onPress}
    >
      <View style={styles.statHeader}>
        <Text style={styles.statTitle}>{title}</Text>
        {icon && (
          <Icon 
            name={icon} 
            size={20} 
            color={iconColor || COLORS.primary} 
          />
        )}
      </View>
      <Text style={styles.statValue}>{value}</Text>
      {change && (
        <View style={styles.statChange}>
          <Icon 
            name={getChangeIcon()} 
            size={14} 
            color={getChangeColor()} 
          />
          <Text style={[styles.changeText, { color: getChangeColor() }]}>
            {change}
          </Text>
        </View>
      )}
    </Card>
  );
};

const AlertCard = ({ 
  type, 
  severity, 
  message, 
  timestamp, 
  onPress, 
  onDismiss,
  style 
}) => {
  const getSeverityColor = () => {
    switch (severity) {
      case 'critical': return COLORS.error;
      case 'high': return COLORS.warning;
      case 'medium': return COLORS.info;
      case 'low': return COLORS.success;
      default: return COLORS.gray;
    }
  };

  const getSeverityIcon = () => {
    switch (severity) {
      case 'critical': return 'error';
      case 'high': return 'warning';
      case 'medium': return 'info';
      case 'low': return 'check-circle';
      default: return 'help';
    }
  };

  return (
    <Card 
      style={[styles.alertCard, { borderLeftColor: getSeverityColor() }, style]}
      onPress={onPress}
    >
      <View style={styles.alertHeader}>
        <View style={styles.alertInfo}>
          <View style={styles.alertSeverity}>
            <Icon 
              name={getSeverityIcon()} 
              size={16} 
              color={getSeverityColor()} 
            />
            <Text style={[styles.severityText, { color: getSeverityColor() }]}>
              {severity?.toUpperCase() || 'UNKNOWN'}
            </Text>
          </View>
          <Text style={styles.alertType}>{type}</Text>
        </View>
        {onDismiss && (
          <TouchableOpacity onPress={onDismiss} style={styles.dismissButton}>
            <Icon name="close" size={20} color={COLORS.gray} />
          </TouchableOpacity>
        )}
      </View>
      <Text style={styles.alertMessage}>{message}</Text>
      {timestamp && (
        <Text style={styles.alertTimestamp}>{timestamp}</Text>
      )}
    </Card>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: SIZES.radius,
    padding: SIZES.padding,
    marginVertical: SIZES.base / 2,
    shadowColor: COLORS.black,
    shadowOffset: {
      width: 0,
      height: 2,
    },
    shadowOpacity: 0.1,
    shadowRadius: 3.84,
    elevation: 2,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SIZES.base,
  },
  icon: {
    marginRight: SIZES.base,
  },
  headerText: {
    flex: 1,
  },
  title: {
    ...FONTS.h3,
    color: COLORS.text,
  },
  subtitle: {
    ...FONTS.body3,
    color: COLORS.gray,
    marginTop: 2,
  },
  content: {
    flex: 1,
  },
  // Stat Card
  statCard: {
    flex: 1,
    minHeight: 100,
  },
  statHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: SIZES.base,
  },
  statTitle: {
    ...FONTS.body3,
    color: COLORS.gray,
  },
  statValue: {
    ...FONTS.h1,
    color: COLORS.text,
    marginBottom: SIZES.base / 2,
  },
  statChange: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  changeText: {
    ...FONTS.caption,
    marginLeft: SIZES.base / 2,
  },
  // Alert Card
  alertCard: {
    borderLeftWidth: 4,
  },
  alertHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: SIZES.base,
  },
  alertInfo: {
    flex: 1,
  },
  alertSeverity: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: SIZES.base / 2,
  },
  severityText: {
    ...FONTS.caption,
    fontWeight: 'bold',
    marginLeft: SIZES.base / 2,
  },
  alertType: {
    ...FONTS.body3,
    color: COLORS.text,
  },
  dismissButton: {
    padding: SIZES.base / 2,
  },
  alertMessage: {
    ...FONTS.body3,
    color: COLORS.text,
    marginBottom: SIZES.base,
  },
  alertTimestamp: {
    ...FONTS.caption,
    color: COLORS.gray,
  },
});

export { Card, StatCard, AlertCard };
export default Card;
